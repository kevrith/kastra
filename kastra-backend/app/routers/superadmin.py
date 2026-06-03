import json
import math
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.admin_audit_log import AdminAuditLog
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.quotation import Quotation
from app.models.subscription_payment import SubscriptionPayment
from app.models.supplier import Supplier, SupplierRequest
from app.models.user import User
from app.utils.billing_events import record_audit, record_subscription_payment
from app.utils.plan_limits import PLAN_PRICES_KES, VALID_PLANS, get_limits
from app.utils.security import hash_password

router = APIRouter(prefix="/api/superadmin", tags=["superadmin"])
_bearer = HTTPBearer()

_SA_ALGORITHM = "HS256"
_SA_EXPIRE_HOURS = 8


def _create_sa_token() -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=_SA_EXPIRE_HOURS)
    return jwt.encode({"sub": "superadmin", "exp": exp}, settings.superadmin_secret_key, algorithm=_SA_ALGORITHM)


def _verify_sa_token(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    try:
        payload = jwt.decode(credentials.credentials, settings.superadmin_secret_key, algorithms=[_SA_ALGORITHM])
        if payload.get("sub") != "superadmin":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authorised")
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired superadmin token")


class SALoginRequest(BaseModel):
    username: str
    password: str


class ChangePlanRequest(BaseModel):
    plan: str
    plan_status: str = "active"


class ExtendTrialRequest(BaseModel):
    days: int = 7


class RecordPaymentRequest(BaseModel):
    plan: str
    amount_kes: int
    payment_method: str = "manual"
    reference: str | None = None
    note: str | None = None


class GrantComplimentaryRequest(BaseModel):
    plan: str
    reason: str
    days: int | None = None  # None = indefinite


class ChangeUserRoleRequest(BaseModel):
    role: str


@router.post("/login")
async def superadmin_login(payload: SALoginRequest):
    if payload.username != settings.superadmin_username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if payload.password != settings.superadmin_password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return {"access_token": _create_sa_token(), "token_type": "bearer"}


@router.get("/stats", dependencies=[Depends(_verify_sa_token)])
async def superadmin_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    seven_days = now + timedelta(days=7)

    total_orgs = (await db.execute(select(func.count()).select_from(Organization))).scalar_one()
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_invoices = (await db.execute(select(func.count()).select_from(Invoice))).scalar_one()

    new_orgs_this_month = (await db.execute(
        select(func.count()).select_from(Organization).where(Organization.created_at >= start_of_month)
    )).scalar_one()

    invoices_this_month = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.created_at >= start_of_month)
    )).scalar_one()

    # Orgs that created at least one invoice this month (engaged)
    active_orgs = (await db.execute(
        select(func.count()).select_from(Organization).where(Organization.invoices_this_month > 0)
    )).scalar_one()

    # Trial counts
    trials_active = (await db.execute(
        select(func.count()).select_from(Organization).where(
            Organization.is_trial == True, Organization.trial_ends_at > now  # noqa: E712
        )
    )).scalar_one()

    trials_expiring_7d = (await db.execute(
        select(func.count()).select_from(Organization).where(
            Organization.is_trial == True,  # noqa: E712
            Organization.trial_ends_at > now,
            Organization.trial_ends_at <= seven_days,
        )
    )).scalar_one()

    # Suspended orgs
    suspended_orgs = (await db.execute(
        select(func.count()).select_from(Organization).where(Organization.plan_status == "suspended")
    )).scalar_one()

    # Plan distribution — only real paying customers (active, not trial, not complimentary)
    plan_counts: dict[str, int] = {}
    for plan in VALID_PLANS:
        count = (await db.execute(
            select(func.count()).select_from(Organization).where(
                Organization.plan == plan,
                Organization.is_trial == False,  # noqa: E712
                Organization.plan_status != "complimentary",
            )
        )).scalar_one()
        plan_counts[plan] = count

    # Trial distribution (paid plans on trial)
    trial_counts: dict[str, int] = {}
    for plan in VALID_PLANS:
        if plan == "free":
            continue
        count = (await db.execute(
            select(func.count()).select_from(Organization).where(
                Organization.plan == plan, Organization.is_trial == True  # noqa: E712
            )
        )).scalar_one()
        trial_counts[plan] = count

    # Complimentary accounts
    complimentary_count = (await db.execute(
        select(func.count()).select_from(Organization).where(Organization.plan_status == "complimentary")
    )).scalar_one()

    mrr = sum(count * PLAN_PRICES_KES.get(plan, 0) for plan, count in plan_counts.items())
    arr = mrr * 12

    # Revenue this month from actual payments
    revenue_this_month = (await db.execute(
        select(func.coalesce(func.sum(SubscriptionPayment.amount_kes), 0))
        .where(SubscriptionPayment.created_at >= start_of_month, SubscriptionPayment.status == "completed")
    )).scalar_one()

    # All-time revenue
    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(SubscriptionPayment.amount_kes), 0))
        .where(SubscriptionPayment.status == "completed")
    )).scalar_one()

    # Feature adoption — how many orgs have ever used each feature
    from app.models.expense import Expense
    from app.models.supplier import Supplier, SupplierRequest

    total_quotations = (await db.execute(select(func.count()).select_from(Quotation))).scalar_one()
    total_suppliers = (await db.execute(
        select(func.count()).select_from(Supplier).where(Supplier.status == "active")
    )).scalar_one()
    total_supplier_requests = (await db.execute(select(func.count()).select_from(SupplierRequest))).scalar_one()
    orgs_using_suppliers = (await db.execute(
        select(func.count(func.distinct(Supplier.organization_id))).select_from(Supplier)
    )).scalar_one()
    orgs_using_expenses = (await db.execute(
        select(func.count(func.distinct(Expense.organization_id))).select_from(Expense)
    )).scalar_one()
    orgs_with_etims = (await db.execute(
        select(func.count(func.distinct(Invoice.organization_id))).select_from(Invoice)
        .where(Invoice.etims_cu_invoice_no.isnot(None))
    )).scalar_one()

    # Conversion funnel
    free_orgs = plan_counts.get("free", 0)
    paid_orgs = sum(v for k, v in plan_counts.items() if k != "free")

    return {
        "total_orgs": total_orgs,
        "total_users": total_users,
        "total_invoices": total_invoices,
        "total_quotations": total_quotations,
        "new_orgs_this_month": new_orgs_this_month,
        "invoices_this_month": invoices_this_month,
        "active_orgs": active_orgs,
        "trials_active": trials_active,
        "trials_expiring_7d": trials_expiring_7d,
        "suspended_orgs": suspended_orgs,
        "complimentary_count": complimentary_count,
        "plan_distribution": plan_counts,
        "trial_distribution": trial_counts,
        "mrr_kes": mrr,
        "arr_kes": arr,
        "revenue_this_month_kes": int(revenue_this_month),
        "total_revenue_kes": int(total_revenue),
        "total_suppliers": total_suppliers,
        "total_supplier_requests": total_supplier_requests,
        "orgs_using_suppliers": orgs_using_suppliers,
        "orgs_using_expenses": orgs_using_expenses,
        "orgs_with_etims": orgs_with_etims,
        "free_orgs": free_orgs,
        "paid_orgs": paid_orgs,
    }


@router.get("/revenue", dependencies=[Depends(_verify_sa_token)])
async def revenue_breakdown(db: AsyncSession = Depends(get_db)):
    """Last 6 months revenue by month + payment method breakdown."""
    now = datetime.now(timezone.utc)
    months = []
    for i in range(5, -1, -1):
        # go back i full months
        month_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_dt = month_dt.replace(month=((month_dt.month - 1 - i) % 12) + 1)
        if month_dt.month > now.month - i:
            month_dt = month_dt.replace(year=now.year - 1)
        else:
            month_dt = month_dt.replace(year=now.year)
        months.append(month_dt)

    # Simpler: just compute from raw SQL
    rows = await db.execute(
        select(
            func.date_trunc("month", SubscriptionPayment.created_at).label("month"),
            func.sum(SubscriptionPayment.amount_kes).label("total"),
            SubscriptionPayment.payment_method,
        )
        .where(
            SubscriptionPayment.status == "completed",
            SubscriptionPayment.created_at >= now - timedelta(days=180),
        )
        .group_by("month", SubscriptionPayment.payment_method)
        .order_by("month")
    )
    raw = rows.all()

    monthly: dict[str, dict] = {}
    for row in raw:
        key = row.month.strftime("%Y-%m") if row.month else "unknown"
        if key not in monthly:
            monthly[key] = {"month": key, "total": 0, "mpesa": 0, "paystack": 0, "manual": 0}
        monthly[key]["total"] += int(row.total or 0)
        method = row.payment_method or "manual"
        if method in monthly[key]:
            monthly[key][method] += int(row.total or 0)

    # Plan revenue breakdown (all time)
    plan_rows = await db.execute(
        select(
            SubscriptionPayment.plan,
            func.sum(SubscriptionPayment.amount_kes).label("total"),
            func.count(SubscriptionPayment.id).label("count"),
        )
        .where(SubscriptionPayment.status == "completed")
        .group_by(SubscriptionPayment.plan)
    )
    plan_revenue = [
        {"plan": r.plan, "total_kes": int(r.total or 0), "payment_count": r.count}
        for r in plan_rows.all()
    ]

    return {
        "monthly": list(monthly.values()),
        "by_plan": plan_revenue,
    }


@router.get("/payments", dependencies=[Depends(_verify_sa_token)])
async def list_payments(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    plan: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(SubscriptionPayment).where(SubscriptionPayment.status == "completed")
    if plan:
        q = q.where(SubscriptionPayment.plan == plan)
    if method:
        q = q.where(SubscriptionPayment.payment_method == method)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = await db.execute(q.order_by(SubscriptionPayment.created_at.desc()).offset((page - 1) * limit).limit(limit))
    payments = rows.scalars().all()

    return {
        "data": [
            {
                "id": str(p.id),
                "org_id": str(p.organization_id),
                "org_name": p.org_name,
                "amount_kes": p.amount_kes,
                "plan": p.plan,
                "payment_method": p.payment_method,
                "reference": p.reference,
                "created_at": p.created_at.isoformat(),
            }
            for p in payments
        ],
        "meta": {"page": page, "limit": limit, "total": total, "pages": math.ceil(total / max(limit, 1))},
    }


@router.get("/trials", dependencies=[Depends(_verify_sa_token)])
async def list_trials(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Organization)
        .where(Organization.is_trial == True, Organization.trial_ends_at > now)  # noqa: E712
        .order_by(Organization.trial_ends_at.asc())
    )
    orgs = result.scalars().all()
    return [
        {
            "id": str(o.id),
            "name": o.name,
            "email": o.email,
            "plan": o.plan,
            "trial_ends_at": o.trial_ends_at.isoformat() if o.trial_ends_at else None,
            "days_left": max(0, (o.trial_ends_at - now).days) if o.trial_ends_at else 0,
            "created_at": o.created_at.isoformat(),
        }
        for o in orgs
    ]


@router.get("/audit-log", dependencies=[Depends(_verify_sa_token)])
async def get_audit_log(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count()).select_from(AdminAuditLog))).scalar_one()
    rows = await db.execute(
        select(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    entries = rows.scalars().all()
    return {
        "data": [
            {
                "id": str(e.id),
                "action": e.action,
                "org_id": e.target_org_id,
                "org_name": e.target_org_name,
                "details": json.loads(e.details) if e.details else None,
                "performed_by": e.performed_by,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ],
        "meta": {"page": page, "limit": limit, "total": total, "pages": math.ceil(total / max(limit, 1))},
    }


@router.get("/organizations", dependencies=[Depends(_verify_sa_token)])
async def list_organizations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    plan: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Organization)
    if plan:
        q = q.where(Organization.plan == plan)
    if status_filter:
        q = q.where(Organization.plan_status == status_filter)
    if search:
        q = q.where(Organization.name.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    orgs_result = await db.execute(
        q.order_by(Organization.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    orgs = orgs_result.scalars().all()

    org_ids = [o.id for o in orgs]
    user_counts: dict = {}
    if org_ids:
        rows = await db.execute(
            select(User.organization_id, func.count(User.id))
            .where(User.organization_id.in_(org_ids))
            .group_by(User.organization_id)
        )
        user_counts = {str(r[0]): r[1] for r in rows}

    now = datetime.now(timezone.utc)
    data = []
    for o in orgs:
        data.append({
            "id": str(o.id),
            "name": o.name,
            "email": o.email,
            "plan": o.plan,
            "plan_status": o.plan_status,
            "is_trial": o.is_trial,
            "trial_ends_at": o.trial_ends_at.isoformat() if o.trial_ends_at else None,
            "days_left_trial": max(0, (o.trial_ends_at - now).days) if o.is_trial and o.trial_ends_at else None,
            "invoices_this_month": o.invoices_this_month,
            "quotations_this_month": o.quotations_this_month,
            "ocr_scans_this_month": o.ocr_scans_this_month,
            "created_at": o.created_at.isoformat(),
            "user_count": user_counts.get(str(o.id), 0),
        })

    return {
        "data": data,
        "meta": {"page": page, "limit": limit, "total": total, "pages": math.ceil(total / max(limit, 1))},
    }


@router.patch("/organizations/{org_id}/plan", dependencies=[Depends(_verify_sa_token)])
async def change_org_plan(
    org_id: str,
    payload: ChangePlanRequest,
    db: AsyncSession = Depends(get_db),
):
    if payload.plan not in VALID_PLANS:
        raise HTTPException(400, f"Invalid plan: {payload.plan}")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")

    old_plan = org.plan
    org.plan = payload.plan
    org.plan_status = payload.plan_status
    org.is_trial = False
    org.trial_ends_at = None
    if payload.plan != "free" and payload.plan_status == "active":
        now = datetime.now(timezone.utc)
        if not org.billing_cycle_start:
            org.billing_cycle_start = now
        org.next_billing_date = now + timedelta(days=30)

    await record_audit(db, "change_plan", org_id, org.name, {
        "old_plan": old_plan, "new_plan": payload.plan, "status": payload.plan_status
    })
    await db.commit()
    return {"message": f"Plan changed from {old_plan} to {payload.plan}", "org_id": org_id}


@router.post("/organizations/{org_id}/unsuspend", dependencies=[Depends(_verify_sa_token)])
async def unsuspend_org(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")
    org.plan_status = "active"
    await record_audit(db, "unsuspend", org_id, org.name)
    await db.commit()
    return {"message": "Organization reactivated", "org_id": org_id}


@router.delete("/organizations/{org_id}/suspend", dependencies=[Depends(_verify_sa_token)])
async def suspend_org(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")
    org.plan_status = "suspended"
    await record_audit(db, "suspend", org_id, org.name)
    await db.commit()
    return {"message": "Organization suspended", "org_id": org_id}


@router.post("/organizations/{org_id}/extend-trial", dependencies=[Depends(_verify_sa_token)])
async def extend_trial(
    org_id: str,
    payload: ExtendTrialRequest,
    db: AsyncSession = Depends(get_db),
):
    if payload.days < 1 or payload.days > 90:
        raise HTTPException(400, "days must be between 1 and 90")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")

    now = datetime.now(timezone.utc)
    base = org.trial_ends_at if org.trial_ends_at and org.trial_ends_at > now else now
    org.trial_ends_at = base + timedelta(days=payload.days)
    org.is_trial = True

    await record_audit(db, "extend_trial", org_id, org.name, {"days_added": payload.days, "new_end": org.trial_ends_at.isoformat()})
    await db.commit()
    return {"message": f"Trial extended by {payload.days} days", "trial_ends_at": org.trial_ends_at.isoformat()}


@router.post("/organizations/{org_id}/record-payment", dependencies=[Depends(_verify_sa_token)])
async def record_manual_payment(
    org_id: str,
    payload: RecordPaymentRequest,
    db: AsyncSession = Depends(get_db),
):
    if payload.plan not in VALID_PLANS:
        raise HTTPException(400, f"Invalid plan: {payload.plan}")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")

    # Activate the plan
    now = datetime.now(timezone.utc)
    org.plan = payload.plan
    org.plan_status = "active"
    org.is_trial = False
    org.trial_ends_at = None
    org.pending_plan = None
    if not org.billing_cycle_start:
        org.billing_cycle_start = now
    org.next_billing_date = now + timedelta(days=30)

    await record_subscription_payment(
        db, org.id, org.name, payload.plan, payload.payment_method,
        reference=payload.reference, amount_kes=payload.amount_kes,
    )
    await record_audit(db, "record_payment", org_id, org.name, {
        "plan": payload.plan, "amount_kes": payload.amount_kes,
        "method": payload.payment_method, "note": payload.note,
    })
    await db.commit()
    return {"message": f"Payment recorded and {payload.plan} plan activated", "org_id": org_id}


@router.post("/organizations/{org_id}/grant-complimentary", dependencies=[Depends(_verify_sa_token)])
async def grant_complimentary(
    org_id: str,
    payload: GrantComplimentaryRequest,
    db: AsyncSession = Depends(get_db),
):
    if payload.plan not in VALID_PLANS or payload.plan == "free":
        raise HTTPException(400, "plan must be starter, business, or premium")
    if not payload.reason.strip():
        raise HTTPException(400, "reason is required")

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")

    now = datetime.now(timezone.utc)
    org.plan = payload.plan
    org.plan_status = "complimentary"
    org.is_trial = False
    org.trial_ends_at = None
    org.pending_plan = None
    org.complimentary_reason = payload.reason.strip()
    org.complimentary_ends_at = now + timedelta(days=payload.days) if payload.days else None
    if not org.billing_cycle_start:
        org.billing_cycle_start = now

    await record_audit(db, "grant_complimentary", org_id, org.name, {
        "plan": payload.plan,
        "reason": payload.reason,
        "days": payload.days,
        "ends_at": org.complimentary_ends_at.isoformat() if org.complimentary_ends_at else "indefinite",
    })
    await db.commit()
    return {
        "message": f"Complimentary {payload.plan} access granted",
        "ends_at": org.complimentary_ends_at.isoformat() if org.complimentary_ends_at else "indefinite",
    }


@router.post("/organizations/{org_id}/revoke-complimentary", dependencies=[Depends(_verify_sa_token)])
async def revoke_complimentary(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")

    org.plan = "free"
    org.plan_status = "active"
    org.complimentary_ends_at = None
    org.complimentary_reason = None

    await record_audit(db, "revoke_complimentary", org_id, org.name)
    await db.commit()
    return {"message": "Complimentary access revoked — org moved to free plan"}


def _generate_temp_password(length: int = 12) -> str:
    """Generate a secure temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


async def _send_temp_password_email(email: str, temp_password: str) -> None:
    """Send temporary password to user."""
    from app.services.email_service import _send
    html = f"""
    <div style="font-family:sans-serif;max-width:520px">
      <h2 style="color:#16a34a">Password Reset by Administrator</h2>
      <p>Your Kastra password has been reset by a system administrator.</p>
      <div style="background:#f3f4f6;border-left:4px solid #16a34a;padding:16px;margin:20px 0">
        <p style="margin:0 0 8px;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:1px">Temporary Password</p>
        <p style="margin:0;font-size:18px;font-family:monospace;font-weight:700;color:#111">{temp_password}</p>
      </div>
      <p style="color:#dc2626;font-weight:600">⚠️ Please change this password immediately after logging in.</p>
      <p><a href="{settings.frontend_url}/login" style="background:#16a34a;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;display:inline-block;font-weight:600">Login to Kastra</a></p>
      <p style="font-size:12px;color:#6b7280;margin-top:24px">For security reasons, this temporary password should only be used once.</p>
    </div>
    """
    await _send(email, "Your Kastra password has been reset", html)


@router.post("/users/{user_id}/reset-password", dependencies=[Depends(_verify_sa_token)])
async def reset_user_password(user_id: str, db: AsyncSession = Depends(get_db)):
    """Generate a temporary password and email it to the user."""
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.organization)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    
    if user.google_id:
        raise HTTPException(400, "Cannot reset password for Google OAuth users")
    
    temp_password = _generate_temp_password()
    user.hashed_password = hash_password(temp_password)
    user.token_version += 1  # Invalidate all existing sessions
    
    await record_audit(db, "reset_user_password", user.organization_id, user.organization.name, {
        "user_id": str(user.id),
        "user_email": user.email,
    })
    await db.commit()
    
    await _send_temp_password_email(user.email, temp_password)
    
    return {"message": f"Password reset for {user.email}. Temporary password sent via email."}


@router.post("/users/{user_id}/deactivate", dependencies=[Depends(_verify_sa_token)])
async def deactivate_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Deactivate a user account."""
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.organization)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    
    if not user.is_active:
        raise HTTPException(400, "User is already inactive")
    
    user.is_active = False
    user.token_version += 1  # Invalidate sessions
    
    await record_audit(db, "deactivate_user", user.organization_id, user.organization.name, {
        "user_id": str(user.id),
        "user_email": user.email,
    })
    await db.commit()
    
    return {"message": f"User {user.email} deactivated"}


@router.post("/users/{user_id}/reactivate", dependencies=[Depends(_verify_sa_token)])
async def reactivate_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Reactivate a user account."""
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.organization)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    
    if user.is_active:
        raise HTTPException(400, "User is already active")
    
    user.is_active = True
    
    await record_audit(db, "reactivate_user", user.organization_id, user.organization.name, {
        "user_id": str(user.id),
        "user_email": user.email,
    })
    await db.commit()
    
    return {"message": f"User {user.email} reactivated"}


@router.patch("/users/{user_id}/role", dependencies=[Depends(_verify_sa_token)])
async def change_user_role(
    user_id: str,
    payload: ChangeUserRoleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role."""
    valid_roles = ["admin", "manager", "field_agent", "viewer"]
    if payload.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    result = await db.execute(select(User).where(User.id == user_id).options(selectinload(User.organization)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    
    old_role = user.role
    user.role = payload.role
    
    await record_audit(db, "change_user_role", user.organization_id, user.organization.name, {
        "user_id": str(user.id),
        "user_email": user.email,
        "old_role": old_role,
        "new_role": payload.role,
    })
    await db.commit()
    
    return {"message": f"User {user.email} role changed from {old_role} to {payload.role}"}


@router.get("/organizations/{org_id}", dependencies=[Depends(_verify_sa_token)])
async def get_org_detail(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")

    users_result = await db.execute(select(User).where(User.organization_id == org_id))
    users = users_result.scalars().all()

    invoice_count = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.organization_id == org_id)
    )).scalar_one()

    quotation_count = (await db.execute(
        select(func.count()).select_from(Quotation).where(Quotation.organization_id == org_id)
    )).scalar_one()

    supplier_count = (await db.execute(
        select(func.count()).select_from(Supplier).where(
            Supplier.organization_id == org_id,
            Supplier.status == "active",
        )
    )).scalar_one()

    supplier_request_count = (await db.execute(
        select(func.count()).select_from(SupplierRequest).where(SupplierRequest.organization_id == org_id)
    )).scalar_one()

    # Last 5 payments for this org
    payments_result = await db.execute(
        select(SubscriptionPayment)
        .where(SubscriptionPayment.organization_id == org_id)
        .order_by(SubscriptionPayment.created_at.desc())
        .limit(5)
    )
    payments = payments_result.scalars().all()

    now = datetime.now(timezone.utc)
    return {
        "id": str(org.id),
        "name": org.name,
        "email": org.email,
        "phone": org.phone,
        "plan": org.plan,
        "plan_status": org.plan_status,
        "is_trial": org.is_trial,
        "trial_ends_at": org.trial_ends_at.isoformat() if org.trial_ends_at else None,
        "days_left_trial": max(0, (org.trial_ends_at - now).days) if org.is_trial and org.trial_ends_at else None,
        "complimentary_ends_at": org.complimentary_ends_at.isoformat() if org.complimentary_ends_at else None,
        "complimentary_reason": org.complimentary_reason,
        "invoices_this_month": org.invoices_this_month,
        "quotations_this_month": org.quotations_this_month,
        "ocr_scans_this_month": org.ocr_scans_this_month,
        "billing_cycle_start": org.billing_cycle_start.isoformat() if org.billing_cycle_start else None,
        "next_billing_date": org.next_billing_date.isoformat() if org.next_billing_date else None,
        "created_at": org.created_at.isoformat(),
        "total_invoices": invoice_count,
        "total_quotations": quotation_count,
        "total_suppliers": supplier_count,
        "total_supplier_requests": supplier_request_count,
        "plan_features": get_limits(org.plan),
        "users": [
            {"id": str(u.id), "email": u.email, "display_name": u.display_name, "role": u.role, "is_active": u.is_active}
            for u in users
        ],
        "recent_payments": [
            {
                "id": str(p.id),
                "amount_kes": p.amount_kes,
                "plan": p.plan,
                "payment_method": p.payment_method,
                "reference": p.reference,
                "created_at": p.created_at.isoformat(),
            }
            for p in payments
        ],
    }
