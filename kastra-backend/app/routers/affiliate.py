import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.affiliate import Affiliate, AffiliateCommission, AffiliatePayout, AffiliateReferral
from app.models.organization import Organization
from app.utils.security import hash_password, verify_password

router = APIRouter(prefix="/api/affiliate", tags=["affiliate"])


# ---------------------------------------------------------------------------
# JWT helpers (affiliate-specific tokens)
# ---------------------------------------------------------------------------

def _create_affiliate_token(affiliate_id: str) -> str:
    from datetime import timedelta
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    return jwt.encode(
        {"sub": affiliate_id, "type": "affiliate_access", "exp": expire},
        settings.secret_key,
        algorithm="HS256",
    )


async def _get_current_affiliate(token: str, db: AsyncSession) -> Affiliate:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "affiliate_access":
            raise JWTError("wrong type")
        aff_id = payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    aff = (await db.execute(select(Affiliate).where(Affiliate.id == uuid.UUID(aff_id)))).scalar_one_or_none()
    if not aff or aff.status != "active":
        raise HTTPException(status_code=401, detail="Affiliate account not found or inactive")
    return aff


# FastAPI dependency
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_bearer = HTTPBearer()


async def get_affiliate(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Affiliate:
    return await _get_current_affiliate(creds.credentials, db)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AffiliateRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    payout_phone: str  # M-Pesa number for commission payouts


class AffiliateLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AffiliateTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AffiliateOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: str
    code: str
    status: str
    payout_phone: str
    balance_ksh: float
    total_earned_ksh: float
    total_paid_ksh: float
    active_referrals: int = 0
    commission_rate_ksh: int = 50

    model_config = {"from_attributes": True}


class ReferralOut(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    plan: str
    is_trial: bool
    is_paying: bool
    joined_at: datetime

    model_config = {"from_attributes": True}


class CommissionOut(BaseModel):
    id: uuid.UUID
    organization_name: str
    month: str
    amount_ksh: float
    created_at: datetime

    model_config = {"from_attributes": True}


class PayoutOut(BaseModel):
    id: uuid.UUID
    amount_ksh: float
    payout_phone: str
    status: str
    failure_reason: str | None
    requested_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PayoutRequest(BaseModel):
    amount_ksh: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_code(name: str, suffix: str) -> str:
    base = "".join(c.upper() for c in name if c.isalpha())[:6]
    return f"{base}{suffix[:4].upper()}"


async def _unique_code(db: AsyncSession, name: str, email: str) -> str:
    base = "".join(c.upper() for c in name if c.isalpha())[:6]
    suffix = email.split("@")[0][:4].upper()
    code = f"{base}{suffix}"
    # Ensure uniqueness
    counter = 1
    while True:
        existing = (await db.execute(select(Affiliate).where(Affiliate.code == code))).scalar_one_or_none()
        if not existing:
            return code
        code = f"{base}{suffix}{counter}"
        counter += 1


async def _paystack_create_recipient(name: str, phone: str, secret_key: str) -> str | None:
    phone_clean = phone.replace("+", "").replace(" ", "")
    if phone_clean.startswith("0"):
        phone_clean = "254" + phone_clean[1:]
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.paystack.co/transferrecipient",
                json={
                    "type": "mobile_money",
                    "name": name,
                    "account_number": phone_clean,
                    "bank_code": "MPESA",
                    "currency": "KES",
                },
                headers={"Authorization": f"Bearer {secret_key}"},
                timeout=15,
            )
            data = resp.json()
            if data.get("status"):
                return data["data"]["recipient_code"]
    except Exception:
        pass
    return None


async def _paystack_transfer(recipient_code: str, amount_ksh: float, reference: str, secret_key: str) -> dict | None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.paystack.co/transfer",
                json={
                    "source": "balance",
                    "amount": int(amount_ksh * 100),  # kobo/cents
                    "recipient": recipient_code,
                    "reason": f"Kastra affiliate commission — ref {reference}",
                    "reference": reference,
                    "currency": "KES",
                },
                headers={"Authorization": f"Bearer {secret_key}"},
                timeout=15,
            )
            data = resp.json()
            if data.get("status"):
                return data["data"]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.post("/register", status_code=201)
async def affiliate_register(payload: AffiliateRegisterRequest, db: AsyncSession = Depends(get_db)):
    if len(payload.password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    existing = (await db.execute(select(Affiliate).where(Affiliate.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Email already registered")

    code = await _unique_code(db, payload.name, payload.email)
    aff = Affiliate(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        code=code,
        payout_phone=payload.payout_phone,
        status="pending",
    )
    db.add(aff)
    await db.commit()
    return {"message": "Application received. You will be notified once approved.", "code": code}


@router.post("/login", response_model=AffiliateTokenResponse)
async def affiliate_login(payload: AffiliateLoginRequest, db: AsyncSession = Depends(get_db)):
    aff = (await db.execute(select(Affiliate).where(Affiliate.email == payload.email))).scalar_one_or_none()
    if not aff or not verify_password(payload.password, aff.password_hash):
        raise HTTPException(401, "Invalid credentials")
    if aff.status == "pending":
        raise HTTPException(403, "Your application is pending approval")
    if aff.status == "suspended":
        raise HTTPException(403, "Your account has been suspended")
    return AffiliateTokenResponse(access_token=_create_affiliate_token(str(aff.id)))


@router.get("/check/{code}")
async def check_code(code: str, db: AsyncSession = Depends(get_db)):
    aff = (await db.execute(
        select(Affiliate).where(Affiliate.code == code.upper(), Affiliate.status == "active")
    )).scalar_one_or_none()
    if not aff:
        raise HTTPException(404, "Referral code not found")
    return {"valid": True, "affiliate_name": aff.name}


# ---------------------------------------------------------------------------
# Affiliate-authenticated endpoints
# ---------------------------------------------------------------------------

@router.get("/me", response_model=AffiliateOut)
async def affiliate_me(aff: Affiliate = Depends(get_affiliate), db: AsyncSession = Depends(get_db)):
    active_count = (await db.execute(
        select(func.count(AffiliateReferral.id))
        .join(Organization, Organization.id == AffiliateReferral.organization_id)
        .where(
            AffiliateReferral.affiliate_id == aff.id,
            Organization.plan != "free",
            Organization.is_trial.is_(False),
        )
    )).scalar() or 0

    return AffiliateOut(
        id=aff.id, name=aff.name, email=aff.email, phone=aff.phone,
        code=aff.code, status=aff.status, payout_phone=aff.payout_phone,
        balance_ksh=float(aff.balance_ksh),
        total_earned_ksh=float(aff.total_earned_ksh),
        total_paid_ksh=float(aff.total_paid_ksh),
        active_referrals=active_count,
        commission_rate_ksh=settings.affiliate_commission_ksh,
    )


@router.get("/referrals", response_model=list[ReferralOut])
async def affiliate_referrals(aff: Affiliate = Depends(get_affiliate), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(AffiliateReferral)
        .where(AffiliateReferral.affiliate_id == aff.id)
        .options(selectinload(AffiliateReferral.organization))
        .order_by(AffiliateReferral.created_at.desc())
    )).scalars().all()

    result = []
    for ref in rows:
        org = ref.organization
        is_paying = org.plan != "free" and not org.is_trial
        result.append(ReferralOut(
            organization_id=org.id,
            organization_name=org.name,
            plan=org.plan,
            is_trial=org.is_trial,
            is_paying=is_paying,
            joined_at=ref.created_at,
        ))
    return result


@router.get("/commissions", response_model=list[CommissionOut])
async def affiliate_commissions(aff: Affiliate = Depends(get_affiliate), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(AffiliateCommission)
        .where(AffiliateCommission.affiliate_id == aff.id)
        .options(selectinload(AffiliateCommission.affiliate))
        .order_by(AffiliateCommission.created_at.desc())
        .limit(200)
    )).scalars().all()

    # Load org names
    org_ids = [r.organization_id for r in rows]
    orgs = {}
    if org_ids:
        org_rows = (await db.execute(select(Organization).where(Organization.id.in_(org_ids)))).scalars().all()
        orgs = {o.id: o.name for o in org_rows}

    return [
        CommissionOut(
            id=r.id, organization_name=orgs.get(r.organization_id, "Unknown"),
            month=r.month, amount_ksh=float(r.amount_ksh), created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/payouts", response_model=list[PayoutOut])
async def affiliate_payouts(aff: Affiliate = Depends(get_affiliate), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(AffiliatePayout)
        .where(AffiliatePayout.affiliate_id == aff.id)
        .order_by(AffiliatePayout.requested_at.desc())
        .limit(50)
    )).scalars().all()
    return [PayoutOut(
        id=r.id, amount_ksh=float(r.amount_ksh), payout_phone=r.payout_phone,
        status=r.status, failure_reason=r.failure_reason,
        requested_at=r.requested_at, completed_at=r.completed_at,
    ) for r in rows]


@router.post("/payout", response_model=PayoutOut)
async def request_payout(payload: PayoutRequest, aff: Affiliate = Depends(get_affiliate), db: AsyncSession = Depends(get_db)):
    amount = payload.amount_ksh
    if amount <= 0:
        raise HTTPException(422, "Amount must be greater than 0")
    if float(aff.balance_ksh) < amount:
        raise HTTPException(400, "Insufficient balance")

    # Create Paystack recipient if not cached
    secret_key = settings.paystack_secret_key
    if not aff.paystack_recipient_code:
        recipient_code = await _paystack_create_recipient(aff.name, aff.payout_phone, secret_key)
        if recipient_code:
            aff.paystack_recipient_code = recipient_code
            await db.flush()

    payout = AffiliatePayout(
        affiliate_id=aff.id,
        amount_ksh=amount,
        payout_phone=aff.payout_phone,
        status="pending",
    )
    db.add(payout)
    await db.flush()

    reference = f"AFF-{aff.id.hex[:8].upper()}-{payout.id.hex[:6].upper()}"
    payout.paystack_reference = reference

    if aff.paystack_recipient_code:
        transfer = await _paystack_transfer(aff.paystack_recipient_code, amount, reference, secret_key)
        if transfer:
            payout.paystack_transfer_code = transfer.get("transfer_code")
            payout.status = "processing"
        else:
            payout.status = "failed"
            payout.failure_reason = "Paystack transfer initiation failed"
    else:
        payout.status = "failed"
        payout.failure_reason = "Could not create Paystack recipient"

    if payout.status == "processing":
        aff.balance_ksh = float(aff.balance_ksh) - amount
        aff.total_paid_ksh = float(aff.total_paid_ksh) + amount

    await db.commit()
    await db.refresh(payout)
    return PayoutOut(
        id=payout.id, amount_ksh=float(payout.amount_ksh), payout_phone=payout.payout_phone,
        status=payout.status, failure_reason=payout.failure_reason,
        requested_at=payout.requested_at, completed_at=payout.completed_at,
    )


# ---------------------------------------------------------------------------
# Paystack transfer webhook
# ---------------------------------------------------------------------------

@router.post("/webhook/paystack")
async def paystack_transfer_webhook(request: dict, db: AsyncSession = Depends(get_db)):
    event = request.get("event", "")
    data = request.get("data", {})
    ref = data.get("reference", "")

    if not ref.startswith("AFF-"):
        return {"ok": True}

    payout = (await db.execute(
        select(AffiliatePayout).where(AffiliatePayout.paystack_reference == ref)
    )).scalar_one_or_none()
    if not payout:
        return {"ok": True}

    if event == "transfer.success":
        payout.status = "completed"
        payout.completed_at = datetime.now(timezone.utc)
    elif event == "transfer.failed" or event == "transfer.reversed":
        payout.status = "failed"
        payout.failure_reason = data.get("reason", "Transfer failed")
        # Refund balance
        aff = (await db.execute(select(Affiliate).where(Affiliate.id == payout.affiliate_id))).scalar_one_or_none()
        if aff:
            aff.balance_ksh = float(aff.balance_ksh) + float(payout.amount_ksh)
            aff.total_paid_ksh = max(0, float(aff.total_paid_ksh) - float(payout.amount_ksh))

    await db.commit()
    return {"ok": True}
