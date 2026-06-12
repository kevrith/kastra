"""
Invoice payments — supports multiple partial payments per invoice.
Recording a payment automatically updates invoice.amount_paid and payment_status.
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
from app.dependencies import get_current_user
from app.models.invoice import Invoice, PaymentDetail
from app.models.invoice_payment import InvoicePayment
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import MessageResponse, Response

router = APIRouter(prefix="/api/invoices", tags=["invoice-payments"])


class PaymentIn(BaseModel):
    amount: float
    method: str  # cash | bank | cheque | mpesa | paystack
    reference: str | None = None
    notes: str | None = None
    paid_at: datetime | None = None


class PaymentOut(BaseModel):
    id: uuid.UUID
    invoice_id: str
    amount: float
    method: str
    reference: str | None
    notes: str | None
    paid_at: datetime

    model_config = {"from_attributes": True}


class InvoiceSummaryOut(BaseModel):
    id: str
    grand_total: float
    amount_paid: float
    balance_due: float
    payment_status: str
    payments: list[PaymentOut]

    model_config = {"from_attributes": True}


def _recalculate_status(inv: Invoice) -> None:
    paid = Decimal(str(inv.amount_paid))
    credited = Decimal(str(inv.amount_credited or 0))
    total = Decimal(str(inv.grand_total))
    covered = paid + credited
    if covered <= 0:
        inv.payment_status = "unpaid"
    elif covered >= total:
        inv.payment_status = "paid"
        if paid > total - credited:
            inv.amount_paid = float(total - credited)  # cap at remaining total
    else:
        inv.payment_status = "partial"


@router.get("/{invoice_id}/payments", response_model=InvoiceSummaryOut)
async def get_payments(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = (await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.organization_id == current_user.organization_id)
        .options(selectinload(Invoice.payments))
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    balance = float(Decimal(str(inv.grand_total)) - Decimal(str(inv.amount_paid)) - Decimal(str(inv.amount_credited or 0)))
    return InvoiceSummaryOut(
        id=inv.id,
        grand_total=float(inv.grand_total),
        amount_paid=float(inv.amount_paid),
        balance_due=max(balance, 0),
        payment_status=inv.payment_status,
        payments=inv.payments,
    )


@router.post("/{invoice_id}/payments", response_model=Response[PaymentOut], status_code=status.HTTP_201_CREATED)
async def record_payment(
    invoice_id: str,
    payload: PaymentIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = (await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.organization_id == current_user.organization_id)
        .options(selectinload(Invoice.payments), selectinload(Invoice.payment_detail))
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already fully paid")

    balance = float(Decimal(str(inv.grand_total)) - Decimal(str(inv.amount_paid)) - Decimal(str(inv.amount_credited or 0)))
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be positive")
    if payload.amount > balance + 0.01:
        raise HTTPException(status_code=400, detail=f"Amount exceeds balance due of KSh {balance:,.2f}")

    paid_at = payload.paid_at or datetime.now(timezone.utc)
    payment = InvoicePayment(
        invoice_id=invoice_id,
        organization_id=current_user.organization_id,
        amount=payload.amount,
        method=payload.method,
        reference=payload.reference,
        notes=payload.notes,
        paid_at=paid_at,
    )
    db.add(payment)

    inv.amount_paid = float(Decimal(str(inv.amount_paid)) + Decimal(str(payload.amount)))
    _recalculate_status(inv)

    # Keep PaymentDetail in sync for the mark-paid case
    if inv.payment_status == "paid" and inv.payment_detail is None:
        db.add(PaymentDetail(
            invoice_id=invoice_id,
            payment_method=payload.method,
            payment_date=paid_at,
            transaction_id=payload.reference,
            notes=payload.notes,
        ))

    # Notify business owner of full payment
    if inv.payment_status == "paid":
        db.add(Notification(
            organization_id=current_user.organization_id,
            type="payment_received",
            title="Payment received",
            body=f"Invoice {invoice_id} has been fully paid — KSh {float(inv.grand_total):,.2f}.",
            entity_id=invoice_id,
        ))

    await db.flush()
    await db.refresh(payment)
    return Response(data=payment)


@router.delete("/{invoice_id}/payments/{payment_id}", response_model=MessageResponse)
async def delete_payment(
    invoice_id: str,
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = (await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.organization_id == current_user.organization_id)
        .options(selectinload(Invoice.payments))
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    payment = next((p for p in inv.payments if p.id == payment_id), None)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    inv.amount_paid = float(Decimal(str(inv.amount_paid)) - Decimal(str(payment.amount)))
    if inv.amount_paid < 0:
        inv.amount_paid = 0
    _recalculate_status(inv)

    await db.delete(payment)
    return MessageResponse(message="Payment deleted")
