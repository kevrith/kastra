"""
Supplier portal — no authentication required.
Suppliers access a unique link to view requested items and submit their prices.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.supplier import (
    SupplierRequestInvite, SupplierRequestItem, SupplierResponseItem,
)

router = APIRouter(prefix="/api/supplier-portal", tags=["supplier-portal"])


class PortalRequestItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: Decimal | None
    unit: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class PortalSupplierOut(BaseModel):
    name: str
    company_name: str | None


class PortalRequestOut(BaseModel):
    request_id: uuid.UUID
    title: str
    notes: str | None
    organization_name: str
    supplier: PortalSupplierOut
    items: list[PortalRequestItemOut]
    status: str  # pending | responded
    submitted_at: datetime | None
    existing_response: list[dict] | None  # pre-filled if already responded


class ResponseItemIn(BaseModel):
    description: str
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal
    notes: str | None = None
    sort_order: int = 0


class SupplierSubmitIn(BaseModel):
    items: list[ResponseItemIn]
    supplier_notes: str | None = None


@router.get("/{token}", response_model=PortalRequestOut)
async def get_portal(
    token: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SupplierRequestInvite).where(SupplierRequestInvite.portal_token == token)
        .options(
            selectinload(SupplierRequestInvite.supplier),
            selectinload(SupplierRequestInvite.request).selectinload(
                SupplierRequestInvite.request.property.mapper.class_.items
            ),
            selectinload(SupplierRequestInvite.response_items),
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="This link is invalid or has expired.")

    # Load org name via request
    from app.models.organization import Organization
    org = await db.get(Organization, invite.request.organization_id)
    org_name = org.name if org else "Business"

    existing = None
    if invite.status == "responded":
        existing = [
            {
                "description": r.description,
                "quantity": float(r.quantity) if r.quantity else None,
                "unit": r.unit,
                "unit_price": float(r.unit_price),
                "notes": r.notes,
                "sort_order": r.sort_order,
            }
            for r in sorted(invite.response_items, key=lambda x: x.sort_order)
        ]

    return PortalRequestOut(
        request_id=invite.request.id,
        title=invite.request.title,
        notes=invite.request.notes,
        organization_name=org_name,
        supplier=PortalSupplierOut(
            name=invite.supplier.name,
            company_name=invite.supplier.company_name,
        ),
        items=[PortalRequestItemOut.model_validate(i) for i in invite.request.items],
        status=invite.status,
        submitted_at=invite.submitted_at,
        existing_response=existing,
    )


@router.post("/{token}/submit", status_code=status.HTTP_200_OK)
async def submit_prices(
    token: uuid.UUID,
    payload: SupplierSubmitIn,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SupplierRequestInvite).where(SupplierRequestInvite.portal_token == token)
        .options(selectinload(SupplierRequestInvite.response_items))
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Please submit at least one item with a price.")

    # Clear previous response if re-submitting
    for old in invite.response_items:
        await db.delete(old)
    await db.flush()

    for i, item in enumerate(payload.items):
        db.add(SupplierResponseItem(
            invite_id=invite.id,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            unit_price=item.unit_price,
            notes=item.notes,
            sort_order=item.sort_order if item.sort_order else i,
        ))

    invite.status = "responded"
    invite.submitted_at = datetime.now(timezone.utc)
    invite.supplier_notes = payload.supplier_notes

    return {"message": "Thank you! Your prices have been submitted successfully."}
