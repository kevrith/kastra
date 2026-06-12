import json
import math
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
import uuid as _uuid
from app.models.admin_audit_log import AdminAuditLog
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.quotation import Quotation
from app.models.subscription_payment import SubscriptionPayment
from app.models.supplier import Supplier, SupplierRequest
from app.models.testimonial import Testimonial
from app.models.user import User
from app.utils.billing_events import record_audit, record_subscription_payment
from app.utils.plan_limits import PLAN_PRICES_KES, VALID_PLANS, get_limits
from app.utils.rate_limit import limiter
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
@limiter.limit("5/minute;20/hour")
async def superadmin_login(request: Request, payload: SALoginRequest):
    # Constant-time comparison on both fields; evaluate both before deciding
    # so a username miss is indistinguishable from a password miss.
    username_ok = secrets.compare_digest(
        payload.username.encode(), settings.superadmin_username.encode()
    )
    password_ok = secrets.compare_digest(
        payload.password.encode(), settings.superadmin_password.encode()
    )
    if not (username_ok and password_ok):
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

    thirty_days_ago = now - timedelta(days=30)

    new_orgs_this_month = (await db.execute(
        select(func.count()).select_from(Organization).where(Organization.created_at >= start_of_month)
    )).scalar_one()

    new_orgs_last_30_days = (await db.execute(
        select(func.count()).select_from(Organization).where(Organization.created_at >= thirty_days_ago)
    )).scalar_one()

    invoices_this_month = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.created_at >= start_of_month)
    )).scalar_one()

    # Orgs active in last 30 days (any invoice OR quotation created)
    orgs_with_invoice_30d = (await db.execute(
        select(func.distinct(Invoice.organization_id)).where(Invoice.created_at >= thirty_days_ago)
    )).scalars().all()
    orgs_with_quote_30d = (await db.execute(
        select(func.distinct(Quotation.organization_id)).where(Quotation.created_at >= thirty_days_ago)
    )).scalars().all()
    active_orgs_30d = len(set(orgs_with_invoice_30d) | set(orgs_with_quote_30d))

    # Legacy: invoices this month (for backward compat)
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

    # Potential MRR if all trial + complimentary orgs converted to their current plan
    potential_mrr = mrr + sum(
        count * PLAN_PRICES_KES.get(plan, 0) for plan, count in trial_counts.items()
    )

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
        "new_orgs_last_30_days": new_orgs_last_30_days,
        "invoices_this_month": invoices_this_month,
        "active_orgs": active_orgs,
        "active_orgs_30d": active_orgs_30d,
        "potential_mrr": potential_mrr,
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
            "next_billing_date": o.next_billing_date.isoformat() if o.next_billing_date else None,
            "days_until_renewal": (o.next_billing_date - now).days if o.next_billing_date and not o.is_trial else None,
            "invoices_this_month": o.invoices_this_month,
            "quotations_this_month": o.quotations_this_month,
            "ocr_scans_this_month": o.ocr_scans_this_month,
            "ai_calls_this_month": o.ai_calls_this_month,
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


@router.delete("/organizations/{org_id}", dependencies=[Depends(_verify_sa_token)])
async def delete_org(org_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text

    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")

    org_name = org.name
    oid = _uuid.UUID(org_id)
    oid_str = str(oid)  # audit_logs stores IDs as plain strings

    try:
        # Delete in FK dependency order — children before parents.
        # quotations.invoice_id → invoices is a circular reference so NULL it first.
        stmts_oid = [
            # Break circular FK: quotations ↔ invoices
            "UPDATE quotations SET invoice_id = NULL WHERE organization_id = :oid",
            # Affiliate sub-tables
            "DELETE FROM affiliate_commissions WHERE organization_id = :oid",
            "DELETE FROM affiliate_referrals   WHERE organization_id = :oid",
            # Supplier sub-tables (response items → invites → request items → requests → suppliers)
            """DELETE FROM supplier_response_items WHERE invite_id IN (
                  SELECT id FROM supplier_request_invites WHERE request_id IN (
                    SELECT id FROM supplier_requests WHERE organization_id = :oid))""",
            """DELETE FROM supplier_request_invites WHERE request_id IN (
                  SELECT id FROM supplier_requests WHERE organization_id = :oid)""",
            """DELETE FROM supplier_request_items WHERE request_id IN (
                  SELECT id FROM supplier_requests WHERE organization_id = :oid)""",
            "DELETE FROM supplier_requests WHERE organization_id = :oid",
            "DELETE FROM suppliers        WHERE organization_id = :oid",
            # Payroll sub-tables
            """DELETE FROM payslips WHERE payroll_run_id IN (
                  SELECT id FROM payroll_runs WHERE organization_id = :oid)""",
            "DELETE FROM payroll_runs WHERE organization_id = :oid",
            "DELETE FROM employees    WHERE organization_id = :oid",
            # Project sub-tables (project_updates/photos cascade via ON DELETE CASCADE on project_id)
            "DELETE FROM project_updates WHERE organization_id = :oid",
            "DELETE FROM project_photos  WHERE organization_id = :oid",
            "DELETE FROM projects        WHERE organization_id = :oid",
            # Invoice sub-tables
            """DELETE FROM payment_details  WHERE invoice_id IN (SELECT id FROM invoices WHERE organization_id = :oid)""",
            """DELETE FROM invoice_items    WHERE invoice_id IN (SELECT id FROM invoices WHERE organization_id = :oid)""",
            """DELETE FROM invoice_charges  WHERE invoice_id IN (SELECT id FROM invoices WHERE organization_id = :oid)""",
            """DELETE FROM invoice_payments WHERE invoice_id IN (SELECT id FROM invoices WHERE organization_id = :oid)""",
            "DELETE FROM invoices WHERE organization_id = :oid",
            # Quotation sub-tables (invoice_id already NULLed above)
            """DELETE FROM quotation_items   WHERE quotation_id IN (SELECT id FROM quotations WHERE organization_id = :oid)""",
            """DELETE FROM quotation_charges WHERE quotation_id IN (SELECT id FROM quotations WHERE organization_id = :oid)""",
            """DELETE FROM quotation_notes   WHERE quotation_id IN (SELECT id FROM quotations WHERE organization_id = :oid)""",
            "DELETE FROM quotations WHERE organization_id = :oid",
            # Other org-level tables
            "DELETE FROM recurring_invoices   WHERE organization_id = :oid",
            "DELETE FROM expenses             WHERE organization_id = :oid",
            "DELETE FROM products             WHERE organization_id = :oid",
            "DELETE FROM client_prices        WHERE organization_id = :oid",
            "DELETE FROM clients              WHERE organization_id = :oid",
            "DELETE FROM notifications        WHERE organization_id = :oid",
            "DELETE FROM subscription_payments WHERE organization_id = :oid",
            "DELETE FROM sequence_counters    WHERE organization_id = :oid",
            # User-level tables (audit_logs.user_id is a plain string, handled separately)
            """DELETE FROM user_permissions WHERE user_id IN (SELECT id FROM users WHERE organization_id = :oid)""",
            "DELETE FROM users WHERE organization_id = :oid",
            # Finally the org itself
            "DELETE FROM organizations WHERE id = :oid",
        ]

        failed_stmt = None
        for stmt in stmts_oid:
            failed_stmt = stmt
            await db.execute(text(stmt), {"oid": oid})

        # audit_logs stores user_id/org_id as plain strings — no FK, clean up separately
        await db.execute(
            text("DELETE FROM audit_logs WHERE organization_id = :oid_str"),
            {"oid_str": oid_str},
        )

        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Delete failed at: {failed_stmt!r} — {exc}",
        ) from exc

    return {"message": f"Organisation '{org_name}' and all its data have been permanently deleted."}


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
      <p><a href="{settings.primary_frontend_url}/login" style="background:#16a34a;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;display:inline-block;font-weight:600">Login to Kastra</a></p>
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
        "ai_calls_this_month": org.ai_calls_this_month,
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


# ── Platform-wide data views ──────────────────────────────────────────────────

@router.get("/invoices", dependencies=[Depends(_verify_sa_token)])
async def sa_list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    org_id: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from app.models.client import Client
    q = (
        select(Invoice, Organization.name.label("org_name"), Client.name.label("client_name"))
        .join(Organization, Invoice.organization_id == Organization.id)
        .join(Client, Invoice.client_id == Client.id)
    )
    if org_id:
        q = q.where(Invoice.organization_id == org_id)
    if payment_status:
        q = q.where(Invoice.payment_status == payment_status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(Invoice.created_at.desc()).offset((page - 1) * limit).limit(limit))).all()
    return {
        "data": [
            {
                "id": r.Invoice.id,
                "org_id": str(r.Invoice.organization_id),
                "org_name": r.org_name,
                "client_name": r.client_name,
                "grand_total": float(r.Invoice.grand_total),
                "payment_status": r.Invoice.payment_status,
                "invoice_date": r.Invoice.invoice_date.isoformat() if r.Invoice.invoice_date else None,
                "created_at": r.Invoice.created_at.isoformat(),
            }
            for r in rows
        ],
        "meta": {"page": page, "limit": limit, "total": total, "pages": math.ceil(total / max(limit, 1))},
    }


@router.get("/quotations", dependencies=[Depends(_verify_sa_token)])
async def sa_list_quotations(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    org_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from app.models.client import Client
    q = (
        select(Quotation, Organization.name.label("org_name"), Client.name.label("client_name"))
        .join(Organization, Quotation.organization_id == Organization.id)
        .join(Client, Quotation.client_id == Client.id)
    )
    if org_id:
        q = q.where(Quotation.organization_id == org_id)
    if status:
        q = q.where(Quotation.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(Quotation.created_at.desc()).offset((page - 1) * limit).limit(limit))).all()
    return {
        "data": [
            {
                "id": r.Quotation.id,
                "org_id": str(r.Quotation.organization_id),
                "org_name": r.org_name,
                "client_name": r.client_name,
                "grand_total": float(r.Quotation.grand_total),
                "status": r.Quotation.status,
                "created_at": r.Quotation.created_at.isoformat(),
            }
            for r in rows
        ],
        "meta": {"page": page, "limit": limit, "total": total, "pages": math.ceil(total / max(limit, 1))},
    }


@router.get("/suppliers", dependencies=[Depends(_verify_sa_token)])
async def sa_list_suppliers(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    org_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from app.models.supplier import Supplier
    q = (
        select(Supplier, Organization.name.label("org_name"))
        .join(Organization, Supplier.organization_id == Organization.id)
        .where(Supplier.status == "active")
    )
    if org_id:
        q = q.where(Supplier.organization_id == org_id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(Supplier.created_at.desc()).offset((page - 1) * limit).limit(limit))).all()
    return {
        "data": [
            {
                "id": str(r.Supplier.id),
                "org_id": str(r.Supplier.organization_id),
                "org_name": r.org_name,
                "name": r.Supplier.name,
                "company_name": r.Supplier.company_name,
                "phone": r.Supplier.phone,
                "email": r.Supplier.email,
                "created_at": r.Supplier.created_at.isoformat(),
            }
            for r in rows
        ],
        "meta": {"page": page, "limit": limit, "total": total, "pages": math.ceil(total / max(limit, 1))},
    }


@router.get("/supplier-requests", dependencies=[Depends(_verify_sa_token)])
async def sa_list_supplier_requests(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    org_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from app.models.supplier import SupplierRequest, SupplierRequestInvite
    q = (
        select(SupplierRequest, Organization.name.label("org_name"))
        .join(Organization, SupplierRequest.organization_id == Organization.id)
    )
    if org_id:
        q = q.where(SupplierRequest.organization_id == org_id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(SupplierRequest.created_at.desc()).offset((page - 1) * limit).limit(limit))).all()

    result = []
    for r in rows:
        inv_count = (await db.execute(
            select(func.count()).select_from(SupplierRequestInvite)
            .where(SupplierRequestInvite.request_id == r.SupplierRequest.id)
        )).scalar_one()
        responded = (await db.execute(
            select(func.count()).select_from(SupplierRequestInvite)
            .where(SupplierRequestInvite.request_id == r.SupplierRequest.id, SupplierRequestInvite.status == "responded")
        )).scalar_one()
        result.append({
            "id": str(r.SupplierRequest.id),
            "org_id": str(r.SupplierRequest.organization_id),
            "org_name": r.org_name,
            "title": r.SupplierRequest.title,
            "status": r.SupplierRequest.status,
            "invites": inv_count,
            "responses": responded,
            "created_at": r.SupplierRequest.created_at.isoformat(),
        })
    return {
        "data": result,
        "meta": {"page": page, "limit": limit, "total": total, "pages": math.ceil(total / max(limit, 1))},
    }


# ── Superadmin document access (view + PDF) ───────────────────────────────────

@router.get("/invoices/{invoice_id}/detail", dependencies=[Depends(_verify_sa_token)])
async def sa_get_invoice(invoice_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload
    from app.models.invoice import Invoice
    from app.schemas.invoice import InvoiceOut
    from app.schemas.organization import OrganizationOut

    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.client),
            selectinload(Invoice.items),
            selectinload(Invoice.charges),
            selectinload(Invoice.payment_detail),
            selectinload(Invoice.expenses),
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invoice not found")

    org = await db.get(Organization, inv.organization_id)
    doc = InvoiceOut.model_validate(inv).model_dump(mode="json")
    org_data = OrganizationOut.model_validate(org).model_dump(mode="json") if org else {}

    await record_audit(db, "sa_view_invoice", str(inv.organization_id), org.name if org else "", {"invoice_id": invoice_id})
    await db.commit()
    return {"invoice": doc, "org": org_data}


@router.get("/invoices/{invoice_id}/pdf", dependencies=[Depends(_verify_sa_token)])
async def sa_invoice_pdf(invoice_id: str, db: AsyncSession = Depends(get_db)):
    import logging
    from fastapi.responses import Response as RawResponse
    from sqlalchemy.orm import selectinload
    from app.models.invoice import Invoice
    from app.schemas.invoice import InvoiceOut
    from app.schemas.organization import OrganizationOut
    from app.services.pdf_service import generate_pdf

    _log = logging.getLogger(__name__)

    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.client),
            selectinload(Invoice.items),
            selectinload(Invoice.charges),
            selectinload(Invoice.payment_detail),
            selectinload(Invoice.expenses),
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Invoice not found")

    org = await db.get(Organization, inv.organization_id)

    # Audit + commit before PDF generation to avoid session conflicts
    await record_audit(db, "sa_print_invoice", str(inv.organization_id), org.name if org else "", {"invoice_id": invoice_id})
    await db.commit()

    try:
        doc = InvoiceOut.model_validate(inv).model_dump(mode="json")
        org_data = OrganizationOut.model_validate(org).model_dump(mode="json") if org else {}
        pdf_bytes = await generate_pdf("invoice", doc, org_data)
    except Exception as exc:
        _log.exception("SA invoice PDF generation failed for %s", invoice_id)
        raise HTTPException(500, f"PDF generation failed: {exc}") from exc

    return RawResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{invoice_id}.pdf"'},
    )


@router.get("/quotations/{quotation_id}/pdf", dependencies=[Depends(_verify_sa_token)])
async def sa_quotation_pdf(quotation_id: str, db: AsyncSession = Depends(get_db)):
    import logging
    from fastapi.responses import Response as RawResponse
    from sqlalchemy.orm import selectinload
    from app.models.quotation import Quotation
    from app.schemas.quotation import QuotationOut
    from app.schemas.organization import OrganizationOut
    from app.services.pdf_service import generate_pdf

    _log = logging.getLogger(__name__)

    result = await db.execute(
        select(Quotation).where(Quotation.id == quotation_id)
        .options(
            selectinload(Quotation.client),
            selectinload(Quotation.items),
            selectinload(Quotation.charges),
            selectinload(Quotation.created_by_user),
        )
    )
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(404, "Quotation not found")

    org = await db.get(Organization, qt.organization_id)

    # Audit + commit before PDF generation to avoid session conflicts
    await record_audit(db, "sa_print_quotation", str(qt.organization_id), org.name if org else "", {"quotation_id": quotation_id})
    await db.commit()

    try:
        doc = QuotationOut.model_validate(qt).model_dump(mode="json")
        org_data = OrganizationOut.model_validate(org).model_dump(mode="json") if org else {}
        pdf_bytes = await generate_pdf("quotation", doc, org_data)
    except Exception as exc:
        _log.exception("SA quotation PDF generation failed for %s", quotation_id)
        raise HTTPException(500, f"PDF generation failed: {exc}") from exc

    return RawResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{quotation_id}.pdf"'},
    )


@router.get("/supplier-requests/{request_id}/detail", dependencies=[Depends(_verify_sa_token)])
async def sa_supplier_request_detail(request_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload
    from app.models.supplier import SupplierRequest, SupplierRequestInvite

    result = await db.execute(
        select(SupplierRequest).where(SupplierRequest.id == request_id)
        .options(
            selectinload(SupplierRequest.items),
            selectinload(SupplierRequest.invites).selectinload(SupplierRequestInvite.supplier),
            selectinload(SupplierRequest.invites).selectinload(SupplierRequestInvite.response_items),
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "Request not found")

    org = await db.get(Organization, req.organization_id)
    await record_audit(db, "sa_view_supplier_request", str(req.organization_id), org.name if org else "", {"request_id": request_id})
    await db.commit()

    return {
        "id": str(req.id),
        "title": req.title,
        "notes": req.notes,
        "status": req.status,
        "org_name": org.name if org else "",
        "items": [{"description": i.description, "quantity": float(i.quantity) if i.quantity else None} for i in req.items],
        "invites": [
            {
                "supplier_name": inv.supplier.name,
                "supplier_company": inv.supplier.company_name,
                "status": inv.status,
                "submitted_at": inv.submitted_at.isoformat() if inv.submitted_at else None,
                "supplier_notes": inv.supplier_notes,
                "response_items": [
                    {"description": r.description, "quantity": float(r.quantity) if r.quantity else None, "unit_price": float(r.unit_price)}
                    for r in sorted(inv.response_items, key=lambda x: x.sort_order)
                ],
            }
            for inv in req.invites
        ],
    }


# ── Testimonials ──────────────────────────────────────────────────────────────

import secrets as _secrets
from datetime import timezone as _tz
from app.services.email_service import (
    send_testimonial_request_email as _send_testimonial_email,
    send_testimonial_whatsapp as _send_testimonial_whatsapp,
    _build_whatsapp_link as _wa_link,
)


class TestimonialIn(BaseModel):
    name: str
    role: str
    text: str
    stars: int = 5
    is_active: bool = True
    sort_order: int = 0


class TestimonialRequestIn(BaseModel):
    email: str = ""   # optional — enables email sending
    name: str
    role_hint: str = ""
    phone: str = ""   # optional — enables WhatsApp sending


class TestimonialRejectIn(BaseModel):
    reason: str = ""


class TestimonialOut(BaseModel):
    id: _uuid.UUID
    name: str
    role: str | None
    text: str | None
    stars: int | None
    is_active: bool
    sort_order: int
    status: str
    requested_email: str | None
    requested_phone: str | None
    submitted_at: str | None
    rejection_reason: str | None

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kw):
        d = {
            "id": obj.id,
            "name": obj.name,
            "role": obj.role,
            "text": obj.text,
            "stars": obj.stars,
            "is_active": obj.is_active,
            "sort_order": obj.sort_order,
            "status": obj.status,
            "requested_email": obj.requested_email,
            "requested_phone": obj.requested_phone,
            "submitted_at": obj.submitted_at.isoformat() if obj.submitted_at else None,
            "rejection_reason": obj.rejection_reason,
        }
        return cls(**d)


@router.get("/testimonials", dependencies=[Depends(_verify_sa_token)])
async def sa_list_testimonials(status: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Testimonial).order_by(Testimonial.sort_order, Testimonial.created_at)
    if status:
        q = q.where(Testimonial.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [TestimonialOut.model_validate(r) for r in rows]


@router.post("/testimonials/request", dependencies=[Depends(_verify_sa_token)])
async def sa_request_testimonial(
    payload: TestimonialRequestIn,
    db: AsyncSession = Depends(get_db),
):
    if not payload.phone.strip():
        raise HTTPException(400, "WhatsApp number is required")

    from datetime import datetime as _dt
    token = _secrets.token_urlsafe(32)
    t = Testimonial(
        id=_uuid.uuid4(),
        name=payload.name,
        role=payload.role_hint or None,
        text=None,
        stars=None,
        is_active=True,
        sort_order=0,
        status="pending",
        request_token=token,
        requested_email=payload.email.strip() or None,
        requested_phone=payload.phone.strip() or None,
        requested_at=_dt.now(_tz.utc),
        consent=False,
    )
    db.add(t)
    await db.commit()

    form_url = f"{settings.primary_frontend_url}/testimonial/{token}"

    sent_via: list[str] = []
    if payload.email.strip():
        await _send_testimonial_email(payload.email.strip(), payload.name, form_url)
        sent_via.append("email")

    whatsapp_link: str | None = None
    whatsapp_sent = False
    if payload.phone.strip():
        whatsapp_link = _wa_link(payload.phone.strip(), form_url, payload.name)
        whatsapp_sent = await _send_testimonial_whatsapp(payload.phone.strip(), payload.name, form_url)
        if whatsapp_sent:
            sent_via.append("WhatsApp")

    contact = payload.email.strip() or payload.phone.strip()
    return {
        "message": f"Request sent to {contact}" + (f" via {' and '.join(sent_via)}" if sent_via else ""),
        "id": str(t.id),
        "whatsapp_link": whatsapp_link,
        "whatsapp_sent": whatsapp_sent,
    }


@router.post("/testimonials/{testimonial_id}/resend", dependencies=[Depends(_verify_sa_token)])
async def sa_resend_testimonial(testimonial_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == _uuid.UUID(testimonial_id))
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Testimonial not found")
    if t.status != "pending" or t.submitted_at is not None:
        raise HTTPException(400, "Can only resend for pending requests not yet submitted")
    if not t.request_token or (not t.requested_email and not t.requested_phone):
        raise HTTPException(400, "No contact info to resend to")

    form_url = f"{settings.primary_frontend_url}/testimonial/{t.request_token}"

    sent_via: list[str] = []
    if t.requested_email:
        await _send_testimonial_email(t.requested_email, t.name, form_url)
        sent_via.append("email")

    whatsapp_link: str | None = None
    whatsapp_sent = False
    if t.requested_phone:
        whatsapp_link = _wa_link(t.requested_phone, form_url, t.name)
        whatsapp_sent = await _send_testimonial_whatsapp(t.requested_phone, t.name, form_url)
        if whatsapp_sent:
            sent_via.append("WhatsApp")

    contact = t.requested_email or t.requested_phone
    return {
        "message": f"Link resent to {contact}" + (f" via {' and '.join(sent_via)}" if sent_via else ""),
        "whatsapp_link": whatsapp_link,
        "whatsapp_sent": whatsapp_sent,
    }


@router.post("/testimonials/{testimonial_id}/approve", dependencies=[Depends(_verify_sa_token)])
async def sa_approve_testimonial(testimonial_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == _uuid.UUID(testimonial_id))
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Testimonial not found")
    t.status = "approved"
    t.is_active = True
    await db.commit()
    return TestimonialOut.model_validate(t)


@router.post("/testimonials/{testimonial_id}/reject", dependencies=[Depends(_verify_sa_token)])
async def sa_reject_testimonial(
    testimonial_id: str,
    payload: TestimonialRejectIn,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == _uuid.UUID(testimonial_id))
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Testimonial not found")
    t.status = "rejected"
    t.is_active = False
    t.rejection_reason = payload.reason or None
    await db.commit()
    return {"message": "Rejected"}


@router.post("/testimonials", dependencies=[Depends(_verify_sa_token)])
async def sa_create_testimonial(payload: TestimonialIn, db: AsyncSession = Depends(get_db)):
    t = Testimonial(
        id=_uuid.uuid4(),
        name=payload.name,
        role=payload.role,
        text=payload.text,
        stars=max(1, min(5, payload.stars)),
        is_active=payload.is_active,
        sort_order=payload.sort_order,
        status="approved",
        consent=True,
    )
    db.add(t)
    await db.commit()
    return TestimonialOut.model_validate(t)


@router.put("/testimonials/{testimonial_id}", dependencies=[Depends(_verify_sa_token)])
async def sa_update_testimonial(
    testimonial_id: str,
    payload: TestimonialIn,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == _uuid.UUID(testimonial_id))
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Testimonial not found")
    t.name = payload.name
    t.role = payload.role
    t.text = payload.text
    t.stars = max(1, min(5, payload.stars))
    t.is_active = payload.is_active
    t.sort_order = payload.sort_order
    await db.commit()
    return TestimonialOut.model_validate(t)


@router.delete("/testimonials/{testimonial_id}", dependencies=[Depends(_verify_sa_token)])
async def sa_delete_testimonial(testimonial_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Testimonial).where(Testimonial.id == _uuid.UUID(testimonial_id))
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Testimonial not found")
    await db.delete(t)
    await db.commit()
    return {"message": "Deleted"}


# ---------------------------------------------------------------------------
# Affiliate management
# ---------------------------------------------------------------------------

from app.models.affiliate import Affiliate, AffiliateReferral, AffiliateCommission, AffiliatePayout
from app.services.email_service import send_affiliate_approved_email


class _AffiliateStatusPatch(BaseModel):
    status: str  # active | suspended | pending


@router.get("/affiliates", dependencies=[Depends(_verify_sa_token)])
async def sa_list_affiliates(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Affiliate).order_by(Affiliate.created_at.desc())
    )).scalars().all()
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "email": a.email,
            "phone": a.phone,
            "code": a.code,
            "status": a.status,
            "payout_phone": a.payout_phone,
            "balance_ksh": float(a.balance_ksh),
            "total_earned_ksh": float(a.total_earned_ksh),
            "total_paid_ksh": float(a.total_paid_ksh),
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]


@router.patch("/affiliates/{affiliate_id}/status", dependencies=[Depends(_verify_sa_token)])
async def sa_update_affiliate_status(affiliate_id: str, payload: _AffiliateStatusPatch, db: AsyncSession = Depends(get_db)):
    aff = (await db.execute(select(Affiliate).where(Affiliate.id == _uuid.UUID(affiliate_id)))).scalar_one_or_none()
    if not aff:
        raise HTTPException(404, "Affiliate not found")
    if payload.status not in ("active", "suspended", "pending"):
        raise HTTPException(422, "Invalid status")
    prev_status = aff.status
    aff.status = payload.status
    await db.commit()
    if payload.status == "active" and prev_status != "active":
        await send_affiliate_approved_email(aff.name, aff.email)
    return {"message": f"Affiliate status updated to {payload.status}"}


@router.get("/affiliates/{affiliate_id}", dependencies=[Depends(_verify_sa_token)])
async def sa_get_affiliate(affiliate_id: str, db: AsyncSession = Depends(get_db)):
    aff = (await db.execute(select(Affiliate).where(Affiliate.id == _uuid.UUID(affiliate_id)))).scalar_one_or_none()
    if not aff:
        raise HTTPException(404, "Affiliate not found")

    referrals = (await db.execute(
        select(AffiliateReferral)
        .where(AffiliateReferral.affiliate_id == aff.id)
        .options(selectinload(AffiliateReferral.organization))
    )).scalars().all()

    commissions = (await db.execute(
        select(AffiliateCommission)
        .where(AffiliateCommission.affiliate_id == aff.id)
        .order_by(AffiliateCommission.created_at.desc())
        .limit(50)
    )).scalars().all()

    payouts = (await db.execute(
        select(AffiliatePayout)
        .where(AffiliatePayout.affiliate_id == aff.id)
        .order_by(AffiliatePayout.requested_at.desc())
        .limit(20)
    )).scalars().all()

    return {
        "id": str(aff.id),
        "name": aff.name,
        "email": aff.email,
        "phone": aff.phone,
        "code": aff.code,
        "status": aff.status,
        "payout_phone": aff.payout_phone,
        "balance_ksh": float(aff.balance_ksh),
        "total_earned_ksh": float(aff.total_earned_ksh),
        "total_paid_ksh": float(aff.total_paid_ksh),
        "commission_rate_ksh": settings.affiliate_commission_ksh,
        "referrals": [
            {
                "org_id": str(r.organization_id),
                "org_name": r.organization.name,
                "plan": r.organization.plan,
                "is_trial": r.organization.is_trial,
                "is_paying": r.organization.plan != "free" and not r.organization.is_trial,
                "joined_at": r.created_at.isoformat(),
            }
            for r in referrals
        ],
        "commissions": [
            {"month": c.month, "amount_ksh": float(c.amount_ksh), "org_id": str(c.organization_id)}
            for c in commissions
        ],
        "payouts": [
            {
                "id": str(p.id),
                "amount_ksh": float(p.amount_ksh),
                "status": p.status,
                "requested_at": p.requested_at.isoformat(),
            }
            for p in payouts
        ],
    }


@router.delete("/affiliates/{affiliate_id}", dependencies=[Depends(_verify_sa_token)])
async def sa_delete_affiliate(affiliate_id: str, db: AsyncSession = Depends(get_db)):
    aff = (await db.execute(select(Affiliate).where(Affiliate.id == _uuid.UUID(affiliate_id)))).scalar_one_or_none()
    if not aff:
        raise HTTPException(404, "Affiliate not found")
    name = aff.name
    # Cascade: delete child records first (referrals keep the org intact — we only remove the link)
    await db.execute(text("DELETE FROM affiliate_payouts     WHERE affiliate_id = :aid"), {"aid": aff.id})
    await db.execute(text("DELETE FROM affiliate_commissions WHERE affiliate_id = :aid"), {"aid": aff.id})
    await db.execute(text("DELETE FROM affiliate_referrals   WHERE affiliate_id = :aid"), {"aid": aff.id})
    await db.delete(aff)
    await db.commit()
    return {"message": f"Affiliate '{name}' has been permanently deleted."}
