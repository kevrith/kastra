"""Procure-to-Pay: purchase orders, negotiation, goods receipts and supplier bills.

Flow: draft -> sent -> (supplier_confirmed | supplier_revised) -> [rejected ↺]
      -> accepted -> receiving -> received -> billed -> paid.
The supplier responds via the no-auth portal (see supplier_portal.py).
"""
import math
import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.product import Product
from app.models.purchase_order import (
    GoodsReceipt, GoodsReceiptItem, PurchaseOrder, PurchaseOrderItem,
    PurchaseOrderNote, SupplierBill, SupplierPriceHistory,
)
from app.models.supplier import Supplier, SupplierRequest, SupplierRequestInvite
from app.models.user import User
from app.schemas.common import MessageResponse, Meta, PaginatedResponse, Response
from app.services.sms_service import send_sms
from app.utils.id_generator import next_id
from app.utils.plan_limits import get_limits

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"])

# Statuses where the buyer may still edit lines / delete the PO
_EDITABLE = {"draft"}
# Statuses where the supplier has come back and the buyer can accept/reject
_NEGOTIABLE = {"supplier_confirmed", "supplier_revised"}


def _money(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── Schemas ───────────────────────────────────────────────────────────────────

class POItemIn(BaseModel):
    product_id: uuid.UUID | None = None
    description: str
    unit: str | None = None
    ordered_qty: Decimal
    ordered_unit_price: Decimal
    sort_order: int = 0


class POCreate(BaseModel):
    supplier_id: uuid.UUID
    currency: str = "KES"
    expected_delivery: date | None = None
    notes: str | None = None
    tax_amount: Decimal = Decimal("0")
    items: list[POItemIn]


class POFromInvice(BaseModel):  # noqa: N801 — create PO from a winning RFQ quote
    invite_id: uuid.UUID


class POItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID | None
    description: str
    unit: str | None
    ordered_qty: Decimal
    ordered_unit_price: Decimal
    confirmed_qty: Decimal | None
    confirmed_unit_price: Decimal | None
    received_qty: Decimal
    line_total: Decimal
    sort_order: int
    # price-change flags (computed)
    last_price: Decimal | None = None      # last price paid this supplier for this item
    price_delta_pct: float | None = None   # confirmed vs ordered, % (supplier's change to your order)
    history_delta_pct: float | None = None  # confirmed/ordered vs last_price, %

    model_config = {"from_attributes": True}


class PONoteOut(BaseModel):
    id: uuid.UUID
    author_type: str
    author_name: str | None
    body: str
    created_at: datetime


class GRNItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal


class GRNOut(BaseModel):
    id: str
    received_date: date
    notes: str | None
    items: list[GRNItemOut]
    created_at: datetime


class POOut(BaseModel):
    id: str
    supplier_id: uuid.UUID
    supplier_name: str
    supplier_phone: str | None
    status: str
    currency: str
    portal_token: uuid.UUID
    portal_url: str
    expected_delivery: date | None
    notes: str | None
    supplier_notes: str | None
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    confirmed_total: Decimal | None
    submitted_at: datetime | None
    accepted_at: datetime | None
    received_at: datetime | None
    items: list[POItemOut]
    notes_thread: list[PONoteOut]
    receipts: list[GRNOut]
    bill_id: str | None
    created_at: datetime
    updated_at: datetime


class POListOut(BaseModel):
    id: str
    supplier_name: str
    status: str
    currency: str
    total: Decimal
    confirmed_total: Decimal | None
    expected_delivery: date | None
    created_at: datetime


# ── Helpers ─────────────────────────────────────────────────────────────────

_load_full = (
    selectinload(PurchaseOrder.supplier),
    selectinload(PurchaseOrder.items),
    selectinload(PurchaseOrder.notes_thread).selectinload(PurchaseOrderNote.author),
)


async def _get_po(db: AsyncSession, po_id: str, org_id: uuid.UUID) -> PurchaseOrder:
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id, PurchaseOrder.organization_id == org_id
        ).options(*_load_full)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


async def _last_price(db: AsyncSession, supplier_id: uuid.UUID, description: str) -> Decimal | None:
    """Most recent price recorded for this supplier + item, for the over-time price flag."""
    row = await db.execute(
        select(SupplierPriceHistory.unit_price)
        .where(
            SupplierPriceHistory.supplier_id == supplier_id,
            SupplierPriceHistory.description == description.strip().lower(),
        )
        .order_by(SupplierPriceHistory.recorded_at.desc())
        .limit(1)
    )
    return row.scalar_one_or_none()


def _pct(new: Decimal, base: Decimal | None) -> float | None:
    if base is None or base == 0:
        return None
    return round(float((new - base) / base * 100), 1)


def _ordered_subtotal(items: list[POItemIn]) -> Decimal:
    return sum((_money(i.ordered_qty) * _money(i.ordered_unit_price) for i in items), Decimal("0"))


async def _to_out(db: AsyncSession, po: PurchaseOrder) -> POOut:
    # bill (if any)
    bill_row = await db.execute(
        select(SupplierBill.id).where(SupplierBill.purchase_order_id == po.id).limit(1)
    )
    bill_id = bill_row.scalar_one_or_none()

    # receipts
    grn_rows = (await db.execute(
        select(GoodsReceipt).where(GoodsReceipt.purchase_order_id == po.id)
        .options(selectinload(GoodsReceipt.items))
        .order_by(GoodsReceipt.created_at)
    )).scalars().all()

    items_out: list[POItemOut] = []
    for i in po.items:
        last = await _last_price(db, po.supplier_id, i.description)
        effective = i.confirmed_unit_price if i.confirmed_unit_price is not None else i.ordered_unit_price
        items_out.append(POItemOut(
            id=i.id, product_id=i.product_id, description=i.description, unit=i.unit,
            ordered_qty=i.ordered_qty, ordered_unit_price=i.ordered_unit_price,
            confirmed_qty=i.confirmed_qty, confirmed_unit_price=i.confirmed_unit_price,
            received_qty=i.received_qty, line_total=i.line_total, sort_order=i.sort_order,
            last_price=last,
            price_delta_pct=(_pct(i.confirmed_unit_price, i.ordered_unit_price)
                             if i.confirmed_unit_price is not None else None),
            history_delta_pct=_pct(_money(effective), last),
        ))

    base_url = settings.primary_frontend_url
    return POOut(
        id=po.id, supplier_id=po.supplier_id, supplier_name=po.supplier.name,
        supplier_phone=po.supplier.phone, status=po.status, currency=po.currency,
        portal_token=po.portal_token, portal_url=f"{base_url}/supplier-order/{po.portal_token}",
        expected_delivery=po.expected_delivery, notes=po.notes, supplier_notes=po.supplier_notes,
        subtotal=po.subtotal, tax_amount=po.tax_amount, total=po.total, confirmed_total=po.confirmed_total,
        submitted_at=po.submitted_at, accepted_at=po.accepted_at, received_at=po.received_at,
        items=sorted(items_out, key=lambda x: x.sort_order),
        notes_thread=[
            PONoteOut(id=n.id, author_type=n.author_type,
                      author_name=(n.author.display_name if n.author else po.supplier.name),
                      body=n.body, created_at=n.created_at)
            for n in po.notes_thread
        ],
        receipts=[
            GRNOut(id=g.id, received_date=g.received_date, notes=g.notes,
                   items=[GRNItemOut(id=it.id, description=it.description, quantity=it.quantity,
                                     unit_price=it.unit_price) for it in g.items],
                   created_at=g.created_at)
            for g in grn_rows
        ],
        bill_id=bill_id,
        created_at=po.created_at, updated_at=po.updated_at,
    )


def _check_plan(org: Organization | None):
    if not get_limits(org.plan if org else "free")["suppliers"]:
        raise HTTPException(status_code=402, detail="Purchase orders are not available on your current plan. Upgrade to Starter or above.")


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[POListOut])
async def list_pos(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func as sqlfunc
    stmt = (
        select(PurchaseOrder).options(selectinload(PurchaseOrder.supplier))
        .where(PurchaseOrder.organization_id == current_user.organization_id)
    )
    if status_filter:
        stmt = stmt.where(PurchaseOrder.status == status_filter)
    total = (await db.execute(select(sqlfunc.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(
        stmt.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )).scalars().all()
    out = [
        POListOut(
            id=p.id, supplier_name=p.supplier.name, status=p.status, currency=p.currency,
            total=p.total, confirmed_total=p.confirmed_total,
            expected_delivery=p.expected_delivery, created_at=p.created_at,
        ) for p in rows
    ]
    return PaginatedResponse(data=out, meta=Meta(page=page, limit=limit, total=total, pages=math.ceil(total / limit) or 1))


@router.post("", response_model=Response[POOut], status_code=status.HTTP_201_CREATED)
async def create_po(
    payload: POCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await db.get(Organization, current_user.organization_id)
    _check_plan(org)

    sup = await db.get(Supplier, payload.supplier_id)
    if not sup or sup.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Add at least one item to the order.")

    subtotal = _ordered_subtotal(payload.items)
    tax = _money(payload.tax_amount)
    po_id = await next_id(db, "purchase_order", current_user.organization_id)
    po = PurchaseOrder(
        id=po_id, organization_id=current_user.organization_id, supplier_id=payload.supplier_id,
        created_by=current_user.id, currency=payload.currency,
        expected_delivery=payload.expected_delivery, notes=payload.notes,
        tax_amount=tax, subtotal=_money(subtotal), total=_money(subtotal + tax),
    )
    db.add(po)
    await db.flush()
    for idx, it in enumerate(payload.items):
        db.add(PurchaseOrderItem(
            purchase_order_id=po.id, product_id=it.product_id, description=it.description,
            unit=it.unit, ordered_qty=_money(it.ordered_qty), ordered_unit_price=_money(it.ordered_unit_price),
            line_total=_money(_money(it.ordered_qty) * _money(it.ordered_unit_price)),
            sort_order=it.sort_order or idx,
        ))
    await db.flush()
    po = await _get_po(db, po.id, current_user.organization_id)
    return Response(data=await _to_out(db, po))


@router.post("/from-request/{request_id}", response_model=Response[POOut], status_code=status.HTTP_201_CREATED)
async def create_po_from_quote(
    request_id: uuid.UUID,
    payload: POFromInvice,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed a PO from a winning supplier quote (RFQ response)."""
    org = await db.get(Organization, current_user.organization_id)
    _check_plan(org)

    result = await db.execute(
        select(SupplierRequestInvite)
        .join(SupplierRequest)
        .where(
            SupplierRequestInvite.id == payload.invite_id,
            SupplierRequestInvite.request_id == request_id,
            SupplierRequest.organization_id == current_user.organization_id,
        )
        .options(
            selectinload(SupplierRequestInvite.response_items),
            selectinload(SupplierRequestInvite.supplier),
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Supplier quote not found")
    if invite.status != "responded" or not invite.response_items:
        raise HTTPException(status_code=400, detail="This supplier has not submitted prices yet.")

    lines = sorted(invite.response_items, key=lambda x: x.sort_order)
    subtotal = sum(
        ((_money(r.quantity) if r.quantity is not None else Decimal("1")) * _money(r.unit_price) for r in lines),
        Decimal("0"),
    )
    po_id = await next_id(db, "purchase_order", current_user.organization_id)
    po = PurchaseOrder(
        id=po_id, organization_id=current_user.organization_id, supplier_id=invite.supplier_id,
        created_by=current_user.id, source_request_id=request_id,
        subtotal=_money(subtotal), total=_money(subtotal),
    )
    db.add(po)
    await db.flush()
    for idx, r in enumerate(lines):
        qty = _money(r.quantity) if r.quantity is not None else Decimal("1")
        db.add(PurchaseOrderItem(
            purchase_order_id=po.id, description=r.description, unit=r.unit,
            ordered_qty=qty, ordered_unit_price=_money(r.unit_price),
            line_total=_money(qty * _money(r.unit_price)), sort_order=idx,
        ))
    await db.flush()
    po = await _get_po(db, po.id, current_user.organization_id)
    return Response(data=await _to_out(db, po))


@router.get("/{po_id}", response_model=Response[POOut])
async def get_po(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = await _get_po(db, po_id, current_user.organization_id)
    return Response(data=await _to_out(db, po))


@router.put("/{po_id}", response_model=Response[POOut])
async def update_po(
    po_id: str,
    payload: POCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = await _get_po(db, po_id, current_user.organization_id)
    if po.status not in _EDITABLE:
        raise HTTPException(status_code=400, detail="Only draft orders can be edited.")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Add at least one item to the order.")

    subtotal = _ordered_subtotal(payload.items)
    tax = _money(payload.tax_amount)
    po.supplier_id = payload.supplier_id
    po.currency = payload.currency
    po.expected_delivery = payload.expected_delivery
    po.notes = payload.notes
    po.tax_amount = tax
    po.subtotal = _money(subtotal)
    po.total = _money(subtotal + tax)
    for old in list(po.items):
        await db.delete(old)
    await db.flush()
    for idx, it in enumerate(payload.items):
        db.add(PurchaseOrderItem(
            purchase_order_id=po.id, product_id=it.product_id, description=it.description,
            unit=it.unit, ordered_qty=_money(it.ordered_qty), ordered_unit_price=_money(it.ordered_unit_price),
            line_total=_money(_money(it.ordered_qty) * _money(it.ordered_unit_price)),
            sort_order=it.sort_order or idx,
        ))
    await db.flush()
    db.expire(po)
    po = await _get_po(db, po_id, current_user.organization_id)
    return Response(data=await _to_out(db, po))


@router.delete("/{po_id}", response_model=MessageResponse)
async def delete_po(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = await _get_po(db, po_id, current_user.organization_id)
    if po.status not in _EDITABLE:
        raise HTTPException(status_code=400, detail="Only draft orders can be deleted. Cancel sent orders instead.")
    await db.delete(po)
    return MessageResponse(message="Purchase order deleted")


# ── Workflow transitions ────────────────────────────────────────────────────

@router.post("/{po_id}/send", response_model=Response[POOut])
async def send_po(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = await _get_po(db, po_id, current_user.organization_id)
    if po.status not in {"draft", "rejected", "supplier_revised", "supplier_confirmed"}:
        raise HTTPException(status_code=400, detail="This order cannot be sent in its current state.")
    po.status = "sent"
    await db.flush()
    link = f"{settings.primary_frontend_url}/supplier-order/{po.portal_token}"
    await send_sms(po.supplier.phone, f"{po.supplier.name}, you have a new purchase order ({po.id}). Review and confirm here: {link}")
    db.expire(po)
    po = await _get_po(db, po_id, current_user.organization_id)
    return Response(data=await _to_out(db, po))


@router.post("/{po_id}/accept", response_model=Response[POOut])
async def accept_po(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = await _get_po(db, po_id, current_user.organization_id)
    if po.status not in _NEGOTIABLE:
        raise HTTPException(status_code=400, detail="The supplier must respond before you can accept.")
    po.status = "accepted"
    po.accepted_at = datetime.now(timezone.utc)
    await db.flush()
    await send_sms(po.supplier.phone, f"{po.supplier.name}, your prices for order {po.id} were accepted. Please proceed with delivery.")
    db.expire(po)
    po = await _get_po(db, po_id, current_user.organization_id)
    return Response(data=await _to_out(db, po))


class POReject(BaseModel):
    reason: str


@router.post("/{po_id}/reject", response_model=Response[POOut])
async def reject_po(
    po_id: str,
    payload: POReject,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = await _get_po(db, po_id, current_user.organization_id)
    if po.status not in _NEGOTIABLE:
        raise HTTPException(status_code=400, detail="There is nothing to reject yet.")
    if not payload.reason.strip():
        raise HTTPException(status_code=400, detail="Please give a reason so the supplier can revise.")
    db.add(PurchaseOrderNote(
        purchase_order_id=po.id, organization_id=current_user.organization_id,
        created_by=current_user.id, author_type="buyer", body=payload.reason.strip(),
    ))
    po.status = "rejected"  # supplier can revise & resubmit; stays visible on their portal
    await db.flush()
    link = f"{settings.primary_frontend_url}/supplier-order/{po.portal_token}"
    await send_sms(po.supplier.phone, f"{po.supplier.name}, your prices for order {po.id} need revision: {payload.reason.strip()[:80]}. Update here: {link}")
    db.expire(po)
    po = await _get_po(db, po_id, current_user.organization_id)
    return Response(data=await _to_out(db, po))


class PONoteIn(BaseModel):
    body: str


@router.post("/{po_id}/notes", response_model=Response[POOut])
async def add_po_note(
    po_id: str,
    payload: PONoteIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = await _get_po(db, po_id, current_user.organization_id)
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="Note cannot be empty.")
    db.add(PurchaseOrderNote(
        purchase_order_id=po.id, organization_id=current_user.organization_id,
        created_by=current_user.id, author_type="buyer", body=payload.body.strip(),
    ))
    await db.flush()
    db.expire(po)
    po = await _get_po(db, po_id, current_user.organization_id)
    return Response(data=await _to_out(db, po))


@router.post("/{po_id}/cancel", response_model=Response[POOut])
async def cancel_po(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    po = await _get_po(db, po_id, current_user.organization_id)
    if po.status in {"received", "billed", "paid", "cancelled"}:
        raise HTTPException(status_code=400, detail="This order can no longer be cancelled.")
    po.status = "cancelled"
    await db.flush()
    db.expire(po)
    po = await _get_po(db, po_id, current_user.organization_id)
    return Response(data=await _to_out(db, po))


# ── Goods Receipt (GRN) ───────────────────────────────────────────────────────

class GRNItemIn(BaseModel):
    purchase_order_item_id: uuid.UUID
    quantity: Decimal  # qty received now


class GRNIn(BaseModel):
    received_date: date | None = None
    notes: str | None = None
    items: list[GRNItemIn]


@router.post("/{po_id}/receipts", response_model=Response[POOut], status_code=status.HTTP_201_CREATED)
async def receive_goods(
    po_id: str,
    payload: GRNIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a delivery. Updates received qty, moving-average product cost, and price history."""
    po = await _get_po(db, po_id, current_user.organization_id)
    if po.status not in {"accepted", "receiving"}:
        raise HTTPException(status_code=400, detail="You can only receive goods on an accepted order.")
    if not payload.items:
        raise HTTPException(status_code=400, detail="Record at least one received item.")

    items_by_id = {i.id: i for i in po.items}

    grn_id = await next_id(db, "goods_receipt", current_user.organization_id)
    grn = GoodsReceipt(
        id=grn_id, organization_id=current_user.organization_id, purchase_order_id=po.id,
        received_by=current_user.id, received_date=payload.received_date or date.today(),
        notes=payload.notes,
    )
    db.add(grn)
    await db.flush()

    for idx, line in enumerate(payload.items):
        po_item = items_by_id.get(line.purchase_order_item_id)
        if not po_item:
            raise HTTPException(status_code=400, detail="Received item does not belong to this order.")
        qty = _money(line.quantity)
        if qty <= 0:
            continue
        # cost = confirmed price if supplier confirmed, else ordered price
        cost = po_item.confirmed_unit_price if po_item.confirmed_unit_price is not None else po_item.ordered_unit_price
        cost = _money(cost)

        db.add(GoodsReceiptItem(
            goods_receipt_id=grn.id, purchase_order_item_id=po_item.id,
            description=po_item.description, quantity=qty, unit_price=cost, sort_order=idx,
        ))
        po_item.received_qty = _money(po_item.received_qty) + qty

        # Moving weighted-average cost on the linked product
        if po_item.product_id:
            product = await db.get(Product, po_item.product_id)
            if product and product.organization_id == current_user.organization_id:
                old_cost = _money(product.cost_price or 0)
                # We don't track stock-on-hand, so weight new receipt against the existing
                # unit cost — a pragmatic moving average that converges to true cost.
                new_cost = ((old_cost + cost) / 2) if old_cost > 0 else cost
                product.cost_price = _money(new_cost)

        # Price history for the over-time change flag
        db.add(SupplierPriceHistory(
            organization_id=current_user.organization_id, supplier_id=po.supplier_id,
            product_id=po_item.product_id, description=po_item.description.strip().lower(),
            unit_price=cost, source_po_id=po.id,
        ))

    # Transition: received if everything in, else receiving (partial)
    fully = all(_money(i.received_qty) >= _money(i.confirmed_qty if i.confirmed_qty is not None else i.ordered_qty) for i in po.items)
    po.status = "received" if fully else "receiving"
    if fully:
        po.received_at = datetime.now(timezone.utc)
    await db.flush()
    db.expire(po)
    po = await _get_po(db, po_id, current_user.organization_id)
    return Response(data=await _to_out(db, po))
