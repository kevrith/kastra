"""
Client portal — no authentication required.
Shareable links for clients to view their invoices and quotations.
PIN-protected portals require a short-lived session token (POST /c/{token}/verify).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel, computed_field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.quotation import Quotation
from app.models.notification import Notification
from app.utils.security import verify_password

router = APIRouter(prefix="/api/portal", tags=["portal"])

_PORTAL_SECRET = settings.secret_key + "-portal"
_PORTAL_SESSION_HOURS = 8


def _create_portal_token(client_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_PORTAL_SESSION_HOURS)
    return jwt.encode({"sub": client_id, "exp": expire, "type": "portal_session"}, _PORTAL_SECRET, algorithm="HS256")


def _verify_portal_token(token: str) -> str:
    payload = jwt.decode(token, _PORTAL_SECRET, algorithms=["HS256"])
    if payload.get("type") != "portal_session":
        raise JWTError("Invalid token type")
    return payload["sub"]


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


class PortalInvoiceOut(BaseModel):
    id: str
    grand_total: Decimal
    payment_status: str
    due_date: datetime | None
    created_at: datetime

    @computed_field
    @property
    def is_overdue(self) -> bool:
        return (
            self.payment_status == "unpaid"
            and self.due_date is not None
            and self.due_date < datetime.now(timezone.utc)
        )

    model_config = {"from_attributes": True}


class PortalQuotationOut(BaseModel):
    id: str
    grand_total: Decimal
    status: str
    expires_at: datetime | None
    created_at: datetime

    @computed_field
    @property
    def is_expired(self) -> bool:
        if self.status not in ("draft", "pending") or self.expires_at is None:
            return False
        return self.expires_at < datetime.now(timezone.utc)

    model_config = {"from_attributes": True}


class ClientPortalOut(BaseModel):
    client_name: str
    business_name: str
    invoices: list[PortalInvoiceOut]
    quotations: list[PortalQuotationOut]


class PublicQuotationItemOut(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class PublicQuotationChargeOut(BaseModel):
    description: str
    amount: Decimal
    vat_exempt: bool

    model_config = {"from_attributes": True}


class PublicQuotationOut(BaseModel):
    id: str
    business_name: str
    business_phone: str | None
    business_email: str | None
    client_name: str
    notes: str | None
    subtotal: Decimal
    vat_amount: Decimal
    charges_total: Decimal
    total_discount: Decimal
    discount_pct: Decimal
    wht_pct: Decimal
    wht_amount: Decimal
    grand_total: Decimal
    status: str
    expires_at: datetime | None
    created_at: datetime
    items: list[PublicQuotationItemOut]
    charges: list[PublicQuotationChargeOut] = []

    @computed_field
    @property
    def is_expired(self) -> bool:
        if self.status not in ("draft", "pending") or self.expires_at is None:
            return False
        return self.expires_at < datetime.now(timezone.utc)


class QuotationRespondRequest(BaseModel):
    action: str  # "accept" | "decline"
    decline_reason: str | None = None


class PinVerifyRequest(BaseModel):
    pin: str


@router.post("/c/{token}/verify")
async def verify_portal_pin(token: str, payload: PinVerifyRequest, db: AsyncSession = Depends(get_db)):
    """Verify the portal PIN and return a short-lived session token."""
    result = await db.execute(select(Client).where(Client.portal_token == token))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Portal not found")
    if not client.portal_pin_hash:
        raise HTTPException(status_code=400, detail="This portal does not require a PIN")
    if not verify_password(payload.pin, client.portal_pin_hash):
        raise HTTPException(status_code=401, detail="Incorrect PIN")
    session_token = _create_portal_token(str(client.id))
    return {"session_token": session_token}


@router.get("/c/{token}", response_model=ClientPortalOut)
async def get_client_portal(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Client)
        .where(Client.portal_token == token)
        .options(selectinload(Client.organization))
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Portal not found")

    # If a PIN is set, require a valid portal session token
    if client.portal_pin_hash:
        bearer = _extract_bearer(request)
        if not bearer:
            raise HTTPException(status_code=403, detail="PIN required", headers={"X-Pin-Required": "true"})
        try:
            client_id_from_token = _verify_portal_token(bearer)
            if client_id_from_token != str(client.id):
                raise HTTPException(status_code=403, detail="Invalid portal session")
        except JWTError:
            raise HTTPException(status_code=403, detail="PIN required", headers={"X-Pin-Required": "true"})

    inv_result = await db.execute(
        select(Invoice)
        .where(Invoice.client_id == client.id)
        .order_by(Invoice.created_at.desc())
    )
    invoices = inv_result.scalars().all()

    qt_result = await db.execute(
        select(Quotation)
        .where(Quotation.client_id == client.id)
        .order_by(Quotation.created_at.desc())
    )
    quotations = qt_result.scalars().all()

    return ClientPortalOut(
        client_name=client.name,
        business_name=client.organization.name,
        invoices=[PortalInvoiceOut.model_validate(i) for i in invoices],
        quotations=[PortalQuotationOut.model_validate(q) for q in quotations],
    )


@router.get("/q/{quotation_id}", response_model=PublicQuotationOut)
async def get_public_quotation(quotation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Quotation)
        .where(Quotation.id == quotation_id)
        .options(
            selectinload(Quotation.client),
            selectinload(Quotation.items),
            selectinload(Quotation.charges),
            selectinload(Quotation.organization),
        )
    )
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")

    return PublicQuotationOut(
        id=qt.id,
        business_name=qt.organization.name,
        business_phone=qt.organization.phone,
        business_email=qt.organization.email,
        client_name=qt.client.name,
        notes=qt.notes,
        subtotal=qt.subtotal,
        vat_amount=qt.vat_amount,
        charges_total=qt.charges_total,
        total_discount=qt.total_discount,
        discount_pct=qt.discount_pct,
        wht_pct=qt.wht_pct,
        wht_amount=qt.wht_amount,
        grand_total=qt.grand_total,
        status=qt.status,
        expires_at=qt.expires_at,
        created_at=qt.created_at,
        items=[PublicQuotationItemOut.model_validate(i) for i in qt.items],
        charges=[PublicQuotationChargeOut.model_validate(c) for c in qt.charges],
    )


@router.post("/q/{quotation_id}/respond")
async def respond_to_quotation(
    quotation_id: str,
    payload: QuotationRespondRequest,
    db: AsyncSession = Depends(get_db),
):
    if payload.action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'decline'")

    result = await db.execute(select(Quotation).where(Quotation.id == quotation_id))
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if qt.status not in ("draft", "pending"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot {payload.action} a quotation with status '{qt.status}'",
        )
    if qt.expires_at and qt.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This quotation has expired")

    qt.status = "accepted" if payload.action == "accept" else "declined"
    if payload.action == "decline" and payload.decline_reason:
        qt.decline_reason = payload.decline_reason.strip()

    # Notify the business owner
    notif_type = "quotation_accepted" if payload.action == "accept" else "quotation_declined"
    notif_title = f"Quotation {qt.status.capitalize()}"
    notif_body = f"Quotation {quotation_id} has been {qt.status} by the client."
    db.add(Notification(
        organization_id=qt.organization_id,
        type=notif_type,
        title=notif_title,
        body=notif_body,
        entity_id=quotation_id,
    ))

    await db.flush()
    return {"message": f"Quotation {payload.action}d successfully", "status": qt.status}
