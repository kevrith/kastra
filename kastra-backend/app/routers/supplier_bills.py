"""Accounts Payable: supplier bills with 3-way match (PO ↔ GRN ↔ Bill) and payments."""
import math
import uuid
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func as sqlfunc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.expense import Expense
from app.models.organization import Organization
from app.models.purchase_order import (
    GoodsReceipt, PurchaseOrder, SupplierBill,
)
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.common import Meta, PaginatedResponse, Response
from app.utils.id_generator import next_id
from app.utils.plan_limits import get_limits

router = APIRouter(prefix="/api/supplier-bills", tags=["supplier-bills"])

_MATCH_TOLERANCE = Decimal("0.01")


def _money(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class BillFromPO(BaseModel):
    supplier_ref: str | None = None       # supplier's own invoice number
    bill_date: date | None = None
    due_date: date | None = None
    tax_amount: Decimal | None = None     # defaults to the PO's tax
    total: Decimal | None = None          # the actual billed total; defaults to received value
    notes: str | None = None
    # For non-resale purchases (no product link), post the bill straight to expenses so it
    # hits the P&L. Leave false for goods-for-resale — those reach P&L via COGS when sold,
    # and double-posting would overstate costs.
    post_to_expenses: bool = False
    expense_category: str = "materials"


class BillOut(BaseModel):
    id: str
    supplier_id: uuid.UUID
    supplier_name: str
    purchase_order_id: str | None
    goods_receipt_id: str | None
    supplier_ref: str | None
    bill_date: date
    due_date: date | None
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    amount_paid: Decimal
    balance: Decimal
    status: str
    match_status: str
    match_notes: str | None
    notes: str | None
    days_overdue: int
    created_at: datetime

    @classmethod
    def build(cls, b: SupplierBill, supplier_name: str) -> "BillOut":
        balance = _money(b.total) - _money(b.amount_paid)
        overdue = 0
        if b.due_date and b.status != "paid":
            overdue = max(0, (date.today() - b.due_date).days)
        return cls(
            id=b.id, supplier_id=b.supplier_id, supplier_name=supplier_name,
            purchase_order_id=b.purchase_order_id, goods_receipt_id=b.goods_receipt_id,
            supplier_ref=b.supplier_ref, bill_date=b.bill_date, due_date=b.due_date,
            subtotal=b.subtotal, tax_amount=b.tax_amount, total=b.total,
            amount_paid=b.amount_paid, balance=balance, status=b.status,
            match_status=b.match_status, match_notes=b.match_notes, notes=b.notes,
            days_overdue=overdue, created_at=b.created_at,
        )


class BillListOut(BaseModel):
    id: str
    supplier_name: str
    total: Decimal
    amount_paid: Decimal
    balance: Decimal
    status: str
    match_status: str
    due_date: date | None
    days_overdue: int
    created_at: datetime


def _check_plan(org: Organization | None):
    if not get_limits(org.plan if org else "free")["suppliers"]:
        raise HTTPException(status_code=402, detail="Supplier bills are not available on your current plan.")


@router.post("/from-po/{po_id}", response_model=Response[BillOut], status_code=status.HTTP_201_CREATED)
async def create_bill_from_po(
    po_id: str,
    payload: BillFromPO,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = await db.get(Organization, current_user.organization_id)
    _check_plan(org)

    po = (await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id, PurchaseOrder.organization_id == current_user.organization_id
        ).options(selectinload(PurchaseOrder.items), selectinload(PurchaseOrder.supplier))
    )).scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status not in {"received", "receiving", "billed"}:
        raise HTTPException(status_code=400, detail="Receive goods before billing this order.")

    existing = (await db.execute(
        select(SupplierBill.id).where(SupplierBill.purchase_order_id == po.id).limit(1)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"A bill ({existing}) already exists for this order.")

    # Value actually received (sum of GRN lines) — the basis for the 3-way match
    grns = (await db.execute(
        select(GoodsReceipt).where(GoodsReceipt.purchase_order_id == po.id)
        .options(selectinload(GoodsReceipt.items))
    )).scalars().all()
    received_value = _money(sum(
        (_money(it.quantity) * _money(it.unit_price) for g in grns for it in g.items),
        Decimal("0"),
    ))
    latest_grn_id = grns[-1].id if grns else None

    tax = _money(payload.tax_amount) if payload.tax_amount is not None else _money(po.tax_amount)
    subtotal = _money(payload.total) - tax if payload.total is not None else received_value
    total = _money(payload.total) if payload.total is not None else _money(received_value + tax)

    # 3-way match: bill total vs received value vs PO confirmed/ordered total
    po_total = _money(po.confirmed_total) if po.confirmed_total is not None else _money(po.total)
    notes_bits = []
    matched = True
    if abs(total - _money(received_value + tax)) > _MATCH_TOLERANCE:
        matched = False
        notes_bits.append(f"Billed {total} vs received value {received_value + tax}.")
    if abs(total - po_total) > _MATCH_TOLERANCE:
        matched = False
        notes_bits.append(f"Billed {total} vs PO total {po_total}.")
    match_status = "matched" if matched else "mismatch"

    bill_id = await next_id(db, "supplier_bill", current_user.organization_id)
    bill = SupplierBill(
        id=bill_id, organization_id=current_user.organization_id, supplier_id=po.supplier_id,
        purchase_order_id=po.id, goods_receipt_id=latest_grn_id,
        supplier_ref=payload.supplier_ref, bill_date=payload.bill_date or date.today(),
        due_date=payload.due_date, subtotal=_money(subtotal), tax_amount=tax, total=total,
        status="unpaid", match_status=match_status,
        match_notes=" ".join(notes_bits) or None, notes=payload.notes,
    )
    db.add(bill)
    po.status = "billed"

    if payload.post_to_expenses:
        db.add(Expense(
            organization_id=current_user.organization_id,
            category=payload.expense_category or "materials",
            description=f"Supplier bill {bill.id} — PO {po.id}",
            vendor=po.supplier.name,
            amount=total,
            date=bill.bill_date,
        ))

    await db.flush()
    await db.refresh(bill)
    return Response(data=BillOut.build(bill, po.supplier.name))


@router.get("", response_model=PaginatedResponse[BillListOut])
async def list_bills(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(SupplierBill, Supplier.name)
        .join(Supplier, Supplier.id == SupplierBill.supplier_id)
        .where(SupplierBill.organization_id == current_user.organization_id)
    )
    if status_filter:
        stmt = stmt.where(SupplierBill.status == status_filter)
    total = (await db.execute(select(sqlfunc.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(
        stmt.order_by(SupplierBill.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )).all()
    out = []
    for b, supplier_name in rows:
        balance = _money(b.total) - _money(b.amount_paid)
        overdue = max(0, (date.today() - b.due_date).days) if (b.due_date and b.status != "paid") else 0
        out.append(BillListOut(
            id=b.id, supplier_name=supplier_name, total=b.total, amount_paid=b.amount_paid,
            balance=balance, status=b.status, match_status=b.match_status,
            due_date=b.due_date, days_overdue=overdue, created_at=b.created_at,
        ))
    return PaginatedResponse(data=out, meta=Meta(page=page, limit=limit, total=total, pages=math.ceil(total / limit) or 1))


@router.get("/summary")
async def payables_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accounts-payable aging buckets for the dashboard."""
    rows = (await db.execute(
        select(SupplierBill).where(
            SupplierBill.organization_id == current_user.organization_id,
            SupplierBill.status != "paid",
        )
    )).scalars().all()
    today = date.today()
    buckets = {"current": Decimal("0"), "overdue_1_30": Decimal("0"), "overdue_31_60": Decimal("0"), "overdue_60_plus": Decimal("0")}
    total_outstanding = Decimal("0")
    for b in rows:
        balance = _money(b.total) - _money(b.amount_paid)
        total_outstanding += balance
        days = (today - b.due_date).days if b.due_date else 0
        if days <= 0:
            buckets["current"] += balance
        elif days <= 30:
            buckets["overdue_1_30"] += balance
        elif days <= 60:
            buckets["overdue_31_60"] += balance
        else:
            buckets["overdue_60_plus"] += balance
    return {
        "total_outstanding": float(_money(total_outstanding)),
        "open_bills": len(rows),
        "aging": {k: float(_money(v)) for k, v in buckets.items()},
    }


@router.get("/{bill_id}", response_model=Response[BillOut])
async def get_bill(
    bill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bill = (await db.execute(
        select(SupplierBill).where(
            SupplierBill.id == bill_id, SupplierBill.organization_id == current_user.organization_id
        ).options(selectinload(SupplierBill.supplier))
    )).scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return Response(data=BillOut.build(bill, bill.supplier.name))


class PaymentIn(BaseModel):
    amount: Decimal
    note: str | None = None


@router.post("/{bill_id}/payments", response_model=Response[BillOut])
async def record_payment(
    bill_id: str,
    payload: PaymentIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bill = (await db.execute(
        select(SupplierBill).where(
            SupplierBill.id == bill_id, SupplierBill.organization_id == current_user.organization_id
        ).options(selectinload(SupplierBill.supplier))
    )).scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    amount = _money(payload.amount)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero.")
    new_paid = _money(bill.amount_paid) + amount
    if new_paid > _money(bill.total) + _MATCH_TOLERANCE:
        raise HTTPException(status_code=400, detail="Payment exceeds the outstanding balance.")
    bill.amount_paid = new_paid
    bill.status = "paid" if new_paid >= _money(bill.total) - _MATCH_TOLERANCE else "partial"

    # If fully paid and the PO is billed, advance it to paid
    if bill.status == "paid" and bill.purchase_order_id:
        po = await db.get(PurchaseOrder, bill.purchase_order_id)
        if po and po.status == "billed":
            po.status = "paid"
    await db.flush()
    await db.refresh(bill)
    return Response(data=BillOut.build(bill, bill.supplier.name))
