import math
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.supplier import (
    Supplier, SupplierRequest, SupplierRequestInvite,
    SupplierRequestItem,
)
from app.models.user import User
from app.schemas.common import MessageResponse, Meta, PaginatedResponse, Response
from app.utils.plan_limits import get_limits

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SupplierIn(BaseModel):
    name: str
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None


class SupplierOut(BaseModel):
    id: uuid.UUID
    name: str
    company_name: str | None
    email: str | None
    phone: str | None
    notes: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RequestItemIn(BaseModel):
    description: str
    quantity: Decimal | None = None
    unit: str | None = None
    sort_order: int = 0


class SupplierRequestIn(BaseModel):
    title: str
    notes: str | None = None
    items: list[RequestItemIn]


class RequestItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: Decimal | None
    unit: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class ResponseItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: Decimal | None
    unit: str | None
    unit_price: Decimal
    notes: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class InviteOut(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    supplier_company: str | None
    supplier_phone: str | None
    portal_token: uuid.UUID
    portal_url: str
    status: str
    submitted_at: datetime | None
    supplier_notes: str | None
    response_items: list[ResponseItemOut]
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_invite(cls, invite: SupplierRequestInvite, base_url: str) -> "InviteOut":
        return cls(
            id=invite.id,
            supplier_id=invite.supplier_id,
            supplier_name=invite.supplier.name,
            supplier_company=invite.supplier.company_name,
            supplier_phone=invite.supplier.phone,
            portal_token=invite.portal_token,
            portal_url=f"{base_url}/supplier-portal/{invite.portal_token}",
            status=invite.status,
            submitted_at=invite.submitted_at,
            supplier_notes=invite.supplier_notes,
            response_items=[ResponseItemOut.model_validate(r) for r in invite.response_items],
            created_at=invite.created_at,
        )


class SupplierRequestOut(BaseModel):
    id: uuid.UUID
    title: str
    notes: str | None
    status: str
    items: list[RequestItemOut]
    invites: list[InviteOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierRequestListOut(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    items_count: int
    responses_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ComparisonRow(BaseModel):
    description: str
    requested_qty: Decimal | None
    unit: str | None
    prices: dict[str, Decimal | None]  # supplier_name → unit_price (None if not quoted)


class ComparisonOut(BaseModel):
    request_id: uuid.UUID
    title: str
    suppliers: list[str]  # ordered list of supplier names
    rows: list[ComparisonRow]
    totals: dict[str, Decimal | None]  # supplier_name → total price


# ── Supplier CRUD ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[SupplierOut])
async def list_suppliers(
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Supplier).where(
        Supplier.organization_id == current_user.organization_id,
        Supplier.status == "active",
    )
    if q:
        stmt = stmt.where(Supplier.name.ilike(f"%{q}%"))
    rows = (await db.execute(stmt.order_by(Supplier.name))).scalars().all()
    return rows


@router.post("", response_model=Response[SupplierOut], status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await db.get(Organization, current_user.organization_id)
    if not get_limits(org.plan if org else "free")["suppliers"]:
        raise HTTPException(status_code=402, detail="Supplier management is not available on your current plan. Upgrade to Starter or above.")

    sup = Supplier(
        organization_id=current_user.organization_id,
        name=payload.name,
        company_name=payload.company_name,
        email=payload.email,
        phone=payload.phone,
        notes=payload.notes,
    )
    db.add(sup)
    await db.flush()
    await db.refresh(sup)
    return Response(data=sup)


@router.put("/{supplier_id}", response_model=Response[SupplierOut])
async def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sup = await db.get(Supplier, supplier_id)
    if not sup or sup.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Supplier not found")
    sup.name = payload.name
    sup.company_name = payload.company_name
    sup.email = payload.email
    sup.phone = payload.phone
    sup.notes = payload.notes
    await db.flush()
    await db.refresh(sup)
    return Response(data=sup)


@router.delete("/{supplier_id}", response_model=MessageResponse)
async def delete_supplier(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sup = await db.get(Supplier, supplier_id)
    if not sup or sup.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Supplier not found")
    sup.status = "inactive"
    return MessageResponse(message="Supplier removed")


# ── Supplier Requests (RFQs) ──────────────────────────────────────────────────

_load_request_full = (
    selectinload(SupplierRequest.items),
    selectinload(SupplierRequest.invites).selectinload(SupplierRequestInvite.supplier),
    selectinload(SupplierRequest.invites).selectinload(SupplierRequestInvite.response_items),
)


def _request_to_out(req: SupplierRequest) -> SupplierRequestOut:
    base_url = settings.primary_frontend_url
    return SupplierRequestOut(
        id=req.id,
        title=req.title,
        notes=req.notes,
        status=req.status,
        items=[RequestItemOut.model_validate(i) for i in req.items],
        invites=[InviteOut.from_invite(inv, base_url) for inv in req.invites],
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


@router.get("/requests", response_model=PaginatedResponse[SupplierRequestListOut])
async def list_requests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func as sqlfunc
    stmt = (
        select(SupplierRequest)
        .options(selectinload(SupplierRequest.items), selectinload(SupplierRequest.invites))
        .where(SupplierRequest.organization_id == current_user.organization_id)
    )
    total = (await db.execute(select(sqlfunc.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await db.execute(stmt.order_by(SupplierRequest.created_at.desc()).offset((page - 1) * limit).limit(limit))
    ).scalars().all()

    out = [
        SupplierRequestListOut(
            id=r.id,
            title=r.title,
            status=r.status,
            items_count=len(r.items),
            responses_count=sum(1 for inv in r.invites if inv.status == "responded"),
            created_at=r.created_at,
        )
        for r in rows
    ]
    return PaginatedResponse(data=out, meta=Meta(page=page, limit=limit, total=total, pages=math.ceil(total / limit) or 1))


@router.post("/requests", response_model=Response[SupplierRequestOut], status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: SupplierRequestIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await db.get(Organization, current_user.organization_id)
    if not get_limits(org.plan if org else "free")["suppliers"]:
        raise HTTPException(status_code=402, detail="Supplier price requests are not available on your current plan. Upgrade to Starter or above.")

    req = SupplierRequest(
        organization_id=current_user.organization_id,
        title=payload.title,
        notes=payload.notes,
    )
    db.add(req)
    await db.flush()

    for i, item in enumerate(payload.items):
        db.add(SupplierRequestItem(
            request_id=req.id,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            sort_order=item.sort_order if item.sort_order else i,
        ))

    await db.flush()
    result = await db.execute(
        select(SupplierRequest).where(SupplierRequest.id == req.id).options(*_load_request_full)
    )
    return Response(data=_request_to_out(result.scalar_one()))


@router.get("/requests/{request_id}", response_model=Response[SupplierRequestOut])
async def get_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SupplierRequest).where(
            SupplierRequest.id == request_id,
            SupplierRequest.organization_id == current_user.organization_id,
        ).options(*_load_request_full)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return Response(data=_request_to_out(req))


@router.put("/requests/{request_id}", response_model=Response[SupplierRequestOut])
async def update_request(
    request_id: uuid.UUID,
    payload: SupplierRequestIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SupplierRequest).where(
            SupplierRequest.id == request_id,
            SupplierRequest.organization_id == current_user.organization_id,
        ).options(selectinload(SupplierRequest.items))
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    req.title = payload.title
    req.notes = payload.notes

    # Replace items: delete old, insert new
    for old_item in req.items:
        await db.delete(old_item)
    await db.flush()

    for i, item in enumerate(payload.items):
        db.add(SupplierRequestItem(
            request_id=req.id,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            sort_order=item.sort_order if item.sort_order else i,
        ))

    await db.flush()
    db.expire(req)
    result2 = await db.execute(
        select(SupplierRequest).where(SupplierRequest.id == request_id).options(*_load_request_full)
    )
    return Response(data=_request_to_out(result2.scalar_one()))


@router.patch("/requests/{request_id}/close", response_model=Response[SupplierRequestOut])
async def close_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SupplierRequest).where(
            SupplierRequest.id == request_id,
            SupplierRequest.organization_id == current_user.organization_id,
        ).options(*_load_request_full)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = "closed"
    await db.flush()
    db.expire(req)
    result2 = await db.execute(
        select(SupplierRequest).where(SupplierRequest.id == request_id).options(*_load_request_full)
    )
    return Response(data=_request_to_out(result2.scalar_one()))


@router.delete("/requests/{request_id}", response_model=MessageResponse)
async def delete_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SupplierRequest).where(
            SupplierRequest.id == request_id,
            SupplierRequest.organization_id == current_user.organization_id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    await db.delete(req)
    return MessageResponse(message="Request deleted")


# ── Invites (send to supplier) ────────────────────────────────────────────────

class InviteIn(BaseModel):
    supplier_id: uuid.UUID


@router.post("/requests/{request_id}/invites", response_model=Response[InviteOut], status_code=status.HTTP_201_CREATED)
async def add_invite(
    request_id: uuid.UUID,
    payload: InviteIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SupplierRequest).where(
            SupplierRequest.id == request_id,
            SupplierRequest.organization_id == current_user.organization_id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    sup = await db.get(Supplier, payload.supplier_id)
    if not sup or sup.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Prevent duplicate invite for same supplier on same request
    existing = await db.execute(
        select(SupplierRequestInvite).where(
            SupplierRequestInvite.request_id == request_id,
            SupplierRequestInvite.supplier_id == payload.supplier_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This supplier has already been invited to this request")

    invite = SupplierRequestInvite(
        request_id=request_id,
        supplier_id=payload.supplier_id,
    )
    db.add(invite)
    await db.flush()
    await db.refresh(invite)

    result2 = await db.execute(
        select(SupplierRequestInvite).where(SupplierRequestInvite.id == invite.id)
        .options(
            selectinload(SupplierRequestInvite.supplier),
            selectinload(SupplierRequestInvite.response_items),
        )
    )
    inv = result2.scalar_one()
    return Response(data=InviteOut.from_invite(inv, settings.primary_frontend_url))


@router.delete("/requests/{request_id}/invites/{invite_id}", response_model=MessageResponse)
async def remove_invite(
    request_id: uuid.UUID,
    invite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SupplierRequestInvite)
        .join(SupplierRequest)
        .where(
            SupplierRequestInvite.id == invite_id,
            SupplierRequestInvite.request_id == request_id,
            SupplierRequest.organization_id == current_user.organization_id,
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invite not found")
    await db.delete(inv)
    return MessageResponse(message="Supplier removed from request")


# ── Comparison ────────────────────────────────────────────────────────────────

@router.get("/requests/{request_id}/comparison", response_model=ComparisonOut)
async def get_comparison(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SupplierRequest).where(
            SupplierRequest.id == request_id,
            SupplierRequest.organization_id == current_user.organization_id,
        ).options(*_load_request_full)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    responded_invites = [inv for inv in req.invites if inv.status == "responded"]
    supplier_names = [inv.supplier.name for inv in responded_invites]

    # Build a lookup: supplier_name → {description → unit_price}
    price_lookup: dict[str, dict[str, Decimal]] = {}
    for inv in responded_invites:
        price_lookup[inv.supplier.name] = {
            item.description.strip().lower(): item.unit_price
            for item in inv.response_items
        }

    # Build rows from the requested items + any extra items suppliers added
    all_descriptions: list[tuple[str, Decimal | None, str | None]] = []
    seen: set[str] = set()
    for item in req.items:
        key = item.description.strip().lower()
        if key not in seen:
            all_descriptions.append((item.description, item.quantity, item.unit))
            seen.add(key)
    # Add extra items that suppliers priced but weren't in the original request
    for inv in responded_invites:
        for resp_item in inv.response_items:
            key = resp_item.description.strip().lower()
            if key not in seen:
                all_descriptions.append((resp_item.description, resp_item.quantity, resp_item.unit))
                seen.add(key)

    rows: list[ComparisonRow] = []
    totals: dict[str, Decimal] = {name: Decimal("0") for name in supplier_names}

    for description, qty, unit in all_descriptions:
        key = description.strip().lower()
        prices: dict[str, Decimal | None] = {}
        for sup_name in supplier_names:
            price = price_lookup.get(sup_name, {}).get(key)
            prices[sup_name] = price
            if price is not None and qty is not None:
                totals[sup_name] += price * qty
            elif price is not None:
                totals[sup_name] += price

        rows.append(ComparisonRow(description=description, requested_qty=qty, unit=unit, prices=prices))

    return ComparisonOut(
        request_id=req.id,
        title=req.title,
        suppliers=supplier_names,
        rows=rows,
        totals={k: v if v > 0 else None for k, v in totals.items()},
    )
