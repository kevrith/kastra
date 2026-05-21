import math
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
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.quotation import Quotation
from app.models.user import User
from app.schemas.common import Meta, PaginatedResponse
from app.utils.plan_limits import PLAN_PRICES_KES, VALID_PLANS
from app.utils.security import verify_password, hash_password

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


class OrgListOut(BaseModel):
    id: str
    name: str
    email: str | None
    plan: str
    plan_status: str
    invoices_this_month: int
    quotations_this_month: int
    ocr_scans_this_month: int
    created_at: datetime
    user_count: int = 0

    model_config = {"from_attributes": True}


class ChangePlanRequest(BaseModel):
    plan: str
    plan_status: str = "active"


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

    total_orgs = (await db.execute(select(func.count()).select_from(Organization))).scalar_one()
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    total_invoices = (await db.execute(select(func.count()).select_from(Invoice))).scalar_one()
    invoices_this_month = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.created_at >= start_of_month)
    )).scalar_one()

    plan_counts: dict[str, int] = {}
    for plan in VALID_PLANS:
        count = (await db.execute(
            select(func.count()).select_from(Organization).where(Organization.plan == plan)
        )).scalar_one()
        plan_counts[plan] = count

    # Monthly Recurring Revenue
    mrr = sum(
        count * PLAN_PRICES_KES.get(plan, 0)
        for plan, count in plan_counts.items()
    )

    return {
        "total_orgs": total_orgs,
        "total_users": total_users,
        "total_invoices": total_invoices,
        "invoices_this_month": invoices_this_month,
        "plan_distribution": plan_counts,
        "mrr_kes": mrr,
    }


@router.get("/organizations", dependencies=[Depends(_verify_sa_token)])
async def list_organizations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    plan: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Organization)
    if plan:
        q = q.where(Organization.plan == plan)
    if search:
        q = q.where(Organization.name.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    orgs_result = await db.execute(
        q.order_by(Organization.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    orgs = orgs_result.scalars().all()

    # Count users per org
    org_ids = [o.id for o in orgs]
    user_counts: dict = {}
    if org_ids:
        rows = await db.execute(
            select(User.organization_id, func.count(User.id)).where(
                User.organization_id.in_(org_ids)
            ).group_by(User.organization_id)
        )
        user_counts = {str(r[0]): r[1] for r in rows}

    data = []
    for o in orgs:
        data.append({
            "id": str(o.id),
            "name": o.name,
            "email": o.email,
            "plan": o.plan,
            "plan_status": o.plan_status,
            "invoices_this_month": o.invoices_this_month,
            "quotations_this_month": o.quotations_this_month,
            "ocr_scans_this_month": o.ocr_scans_this_month,
            "created_at": o.created_at.isoformat(),
            "user_count": user_counts.get(str(o.id), 0),
        })

    return {
        "data": data,
        "meta": {"page": page, "limit": limit, "total": total, "pages": math.ceil(total / limit)},
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
    if payload.plan != "free" and payload.plan_status == "active":
        now = datetime.now(timezone.utc)
        if not org.billing_cycle_start:
            org.billing_cycle_start = now
        org.next_billing_date = now + timedelta(days=30)

    return {"message": f"Plan changed from {old_plan} to {payload.plan}", "org_id": org_id}


@router.delete("/organizations/{org_id}/suspend", dependencies=[Depends(_verify_sa_token)])
async def suspend_org(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")
    org.plan_status = "suspended"
    return {"message": "Organization suspended", "org_id": org_id}


@router.get("/organizations/{org_id}", dependencies=[Depends(_verify_sa_token)])
async def get_org_detail(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")

    users_result = await db.execute(
        select(User).where(User.organization_id == org_id)
    )
    users = users_result.scalars().all()

    invoice_count = (await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.organization_id == org_id)
    )).scalar_one()

    quotation_count = (await db.execute(
        select(func.count()).select_from(Quotation).where(Quotation.organization_id == org_id)
    )).scalar_one()

    return {
        "id": str(org.id),
        "name": org.name,
        "email": org.email,
        "phone": org.phone,
        "plan": org.plan,
        "plan_status": org.plan_status,
        "invoices_this_month": org.invoices_this_month,
        "quotations_this_month": org.quotations_this_month,
        "ocr_scans_this_month": org.ocr_scans_this_month,
        "billing_cycle_start": org.billing_cycle_start.isoformat() if org.billing_cycle_start else None,
        "next_billing_date": org.next_billing_date.isoformat() if org.next_billing_date else None,
        "created_at": org.created_at.isoformat(),
        "total_invoices": invoice_count,
        "total_quotations": quotation_count,
        "users": [
            {"id": str(u.id), "email": u.email, "display_name": u.display_name, "role": u.role, "is_active": u.is_active}
            for u in users
        ],
    }
