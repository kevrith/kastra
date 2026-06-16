"""
Supplier portal — no authentication required.
Suppliers access a unique link to view requested items and submit their prices.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.notification import Notification
from app.models.supplier import (
    SupplierRequestInvite, SupplierResponseItem,
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


# ── Purchase-order portal (order mode) ──────────────────────────────────────────

class PortalOrderItemOut(BaseModel):
    id: uuid.UUID
    description: str
    unit: str | None
    ordered_qty: Decimal
    ordered_unit_price: Decimal
    confirmed_qty: Decimal | None
    confirmed_unit_price: Decimal | None
    sort_order: int

    model_config = {"from_attributes": True}


class PortalOrderNoteOut(BaseModel):
    author_type: str
    body: str
    created_at: datetime


class PortalOrderOut(BaseModel):
    po_id: str
    organization_name: str
    supplier: PortalSupplierOut
    status: str
    currency: str
    expected_delivery: date | None
    notes: str | None
    supplier_notes: str | None
    items: list[PortalOrderItemOut]
    notes_thread: list[PortalOrderNoteOut]
    submitted_at: datetime | None


class OrderRespondItemIn(BaseModel):
    id: uuid.UUID
    confirmed_qty: Decimal
    confirmed_unit_price: Decimal


class OrderRespondIn(BaseModel):
    items: list[OrderRespondItemIn]
    supplier_notes: str | None = None
    reply: str | None = None  # optional reply to a rejection


async def _load_order(db: AsyncSession, token: uuid.UUID) -> "PurchaseOrder":
    from app.models.purchase_order import PurchaseOrder, PurchaseOrderNote
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.portal_token == token).options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.items),
            selectinload(PurchaseOrder.notes_thread),
        )
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="This link is invalid or has expired.")
    return po


@router.get("/order/{token}", response_model=PortalOrderOut)
async def get_order_portal(token: uuid.UUID, db: AsyncSession = Depends(get_db)):
    po = await _load_order(db, token)
    from app.models.organization import Organization
    org = await db.get(Organization, po.organization_id)
    return PortalOrderOut(
        po_id=po.id,
        organization_name=org.name if org else "Business",
        supplier=PortalSupplierOut(name=po.supplier.name, company_name=po.supplier.company_name),
        status=po.status, currency=po.currency, expected_delivery=po.expected_delivery,
        notes=po.notes, supplier_notes=po.supplier_notes,
        items=[PortalOrderItemOut.model_validate(i) for i in sorted(po.items, key=lambda x: x.sort_order)],
        notes_thread=[
            PortalOrderNoteOut(author_type=n.author_type, body=n.body, created_at=n.created_at)
            for n in sorted(po.notes_thread, key=lambda x: x.created_at)
        ],
        submitted_at=po.submitted_at,
    )


@router.post("/order/{token}/respond", status_code=status.HTTP_200_OK)
async def respond_order(token: uuid.UUID, payload: OrderRespondIn, db: AsyncSession = Depends(get_db)):
    from decimal import ROUND_HALF_UP
    from app.models.purchase_order import PurchaseOrderNote

    po = await _load_order(db, token)
    if po.status not in {"sent", "rejected", "supplier_confirmed", "supplier_revised"}:
        raise HTTPException(status_code=400, detail="This order is no longer open for changes.")

    def money(v):
        return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    items_by_id = {i.id: i for i in po.items}
    changed = False
    confirmed_total = Decimal("0")
    for line in payload.items:
        item = items_by_id.get(line.id)
        if not item:
            continue
        item.confirmed_qty = money(line.confirmed_qty)
        item.confirmed_unit_price = money(line.confirmed_unit_price)
        confirmed_total += item.confirmed_qty * item.confirmed_unit_price
        if item.confirmed_qty != money(item.ordered_qty) or item.confirmed_unit_price != money(item.ordered_unit_price):
            changed = True

    po.confirmed_total = money(confirmed_total + money(po.tax_amount))
    po.supplier_notes = payload.supplier_notes
    po.status = "supplier_revised" if changed else "supplier_confirmed"
    po.submitted_at = datetime.now(timezone.utc)

    if payload.reply and payload.reply.strip():
        db.add(PurchaseOrderNote(
            purchase_order_id=po.id, organization_id=po.organization_id,
            created_by=None, author_type="supplier", body=payload.reply.strip(),
        ))

    # Notify the buyer in-app
    verb = "revised the prices/quantities on" if changed else "confirmed"
    db.add(Notification(
        organization_id=po.organization_id, type="po_supplier_response",
        title=f"{po.supplier.name} {('revised' if changed else 'confirmed')} order {po.id}",
        body=f"{po.supplier.name} has {verb} purchase order {po.id}. Review and accept or reject.",
        entity_id=po.id,
    ))
    return {"message": "Thank you! Your response has been sent to the buyer."}
