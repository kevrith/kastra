import logging
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import Response
from app.services.mpesa_service import initiate_stk_push
from app.utils.plan_limits import PLAN_PRICES_KES, PLANS, VALID_PLANS, get_limits

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

PAYSTACK_API = "https://api.paystack.co"


class PlanInfo(BaseModel):
    plan: str
    plan_status: str
    pending_plan: str | None
    is_trial: bool
    trial_ends_at: datetime | None
    invoices_this_month: int
    quotations_this_month: int
    ocr_scans_this_month: int
    billing_cycle_start: datetime | None
    next_billing_date: datetime | None
    limits: dict
    price_kes: int

    model_config = {"from_attributes": True}


class UpgradeRequest(BaseModel):
    plan: str


class MpesaUpgradeRequest(BaseModel):
    plan: str
    phone: str  # 254XXXXXXXXX


class PaystackUpgradeRequest(BaseModel):
    plan: str
    email: str


async def _get_org(db: AsyncSession, org_id) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")
    return org


def _activate_plan(org: Organization, plan: str) -> None:
    """Activate a paid plan after successful payment. Clears trial state."""
    now = datetime.now(timezone.utc)
    org.plan = plan
    org.plan_status = "active"
    org.pending_plan = None
    org.sub_mpesa_checkout_id = None
    org.is_trial = False
    org.trial_ends_at = None
    if plan != "free":
        if not org.billing_cycle_start:
            org.billing_cycle_start = now
        org.next_billing_date = now + timedelta(days=30)


@router.get("/me", response_model=Response[PlanInfo])
async def get_my_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(db, current_user.organization_id)
    limits = get_limits(org.plan)
    return Response(data=PlanInfo(
        plan=org.plan,
        plan_status=org.plan_status,
        pending_plan=org.pending_plan,
        is_trial=org.is_trial,
        trial_ends_at=org.trial_ends_at,
        invoices_this_month=org.invoices_this_month,
        quotations_this_month=org.quotations_this_month,
        ocr_scans_this_month=org.ocr_scans_this_month,
        billing_cycle_start=org.billing_cycle_start,
        next_billing_date=org.next_billing_date,
        limits=dict(limits),
        price_kes=PLAN_PRICES_KES.get(org.plan, 0),
    ))


@router.get("/plans")
async def list_plans():
    return {
        "plans": [
            {"id": pid, "price_kes": PLAN_PRICES_KES[pid], "limits": dict(lims)}
            for pid, lims in PLANS.items()
        ]
    }


@router.post("/upgrade/mpesa")
async def upgrade_via_mpesa(
    payload: MpesaUpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate M-Pesa STK Push for a plan upgrade. Plan activates on callback."""
    if payload.plan not in VALID_PLANS:
        raise HTTPException(400, f"Invalid plan: {payload.plan}")
    if payload.plan == "free":
        raise HTTPException(400, "Downgrade to Free requires no payment — use /upgrade/free")

    org = await _get_org(db, current_user.organization_id)
    price = PLAN_PRICES_KES[payload.plan]

    try:
        checkout_id = await initiate_stk_push(
            phone=payload.phone,
            amount=price,
            account_ref="KASUB",
            description=f"Kastra {payload.plan.capitalize()} plan",
        )
    except Exception as e:
        raise HTTPException(502, f"M-Pesa STK Push failed: {str(e)}")

    org.pending_plan = payload.plan
    org.sub_mpesa_checkout_id = checkout_id
    await db.commit()

    return {
        "message": "STK Push sent. Approve the prompt on your phone.",
        "checkout_request_id": checkout_id,
        "plan": payload.plan,
        "amount": price,
    }


@router.post("/upgrade/paystack")
async def upgrade_via_paystack(
    payload: PaystackUpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initialize a Paystack payment for a plan upgrade. Returns the hosted payment URL."""
    if payload.plan not in VALID_PLANS:
        raise HTTPException(400, f"Invalid plan: {payload.plan}")
    if payload.plan == "free":
        raise HTTPException(400, "Downgrade to Free requires no payment — use /upgrade/free")

    org = await _get_org(db, current_user.organization_id)
    price = PLAN_PRICES_KES[payload.plan]
    amount_kobo = price * 100

    reference = f"SUB-{org.id}-{int(datetime.now().timestamp())}"
    callback_url = f"{settings.frontend_url}/settings?sub_ref={reference}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYSTACK_API}/transaction/initialize",
            headers={
                "Authorization": f"Bearer {settings.paystack_secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "email": payload.email,
                "amount": amount_kobo,
                "reference": reference,
                "callback_url": callback_url,
                "currency": "KES",
                "metadata": {
                    "type": "subscription",
                    "plan": payload.plan,
                    "org_id": str(org.id),
                },
            },
        )

    if not resp.is_success:
        detail = resp.json().get("message", "Paystack initialization failed")
        raise HTTPException(502, detail)

    data = resp.json()["data"]
    org.pending_plan = payload.plan
    await db.commit()

    return {
        "authorization_url": data["authorization_url"],
        "reference": data["reference"],
        "plan": payload.plan,
        "amount": price,
    }


@router.get("/upgrade/paystack/verify/{reference}")
async def verify_paystack_upgrade(
    reference: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a Paystack subscription payment after redirect and activate the plan."""
    org = await _get_org(db, current_user.organization_id)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PAYSTACK_API}/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {settings.paystack_secret_key}"},
        )

    if not resp.is_success:
        raise HTTPException(502, "Could not reach Paystack to verify payment")

    data = resp.json().get("data", {})
    if data.get("status") != "success":
        return {"status": "failed", "message": "Payment was not successful"}

    # Confirm the payment matches the org and plan
    meta = data.get("metadata", {})
    plan_from_meta = meta.get("plan") or org.pending_plan
    org_id_from_meta = meta.get("org_id")

    if org_id_from_meta and org_id_from_meta != str(org.id):
        raise HTTPException(403, "Payment does not belong to your organisation")

    if not plan_from_meta or plan_from_meta not in VALID_PLANS:
        raise HTTPException(400, "Could not determine plan from payment")

    _activate_plan(org, plan_from_meta)
    await db.commit()
    logger.info("Paystack subscription activated: org=%s plan=%s ref=%s", org.id, plan_from_meta, reference)

    return {
        "status": "success",
        "plan": org.plan,
        "message": f"Upgraded to {org.plan.capitalize()} plan successfully.",
    }


@router.post("/upgrade/free")
async def downgrade_to_free(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Immediately downgrade to the free plan — no payment required."""
    org = await _get_org(db, current_user.organization_id)
    if org.plan == "free":
        raise HTTPException(400, "Already on the free plan")
    old = org.plan
    org.plan = "free"
    org.plan_status = "active"
    org.pending_plan = None
    org.next_billing_date = None
    await db.commit()
    return {"message": f"Downgraded from {old} to free plan", "plan": "free"}
