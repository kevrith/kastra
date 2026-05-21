"""
Public payment portal — no authentication required.
Customers use these endpoints to view and pay their invoices
via a shareable link: /pay/{invoice_id}
"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.invoice import Invoice
from app.services.mpesa_service import initiate_stk_push

router = APIRouter(prefix="/api/pay", tags=["pay"])


class PublicInvoiceOut(BaseModel):
    id: str
    business_name: str
    client_name: str
    client_email: str | None
    grand_total: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    payment_status: str
    due_date: datetime | None
    created_at: datetime


class PublicMpesaRequest(BaseModel):
    phone_number: str  # 254XXXXXXXXX
    amount: float | None = None  # optional partial amount


@router.get("/{invoice_id}", response_model=PublicInvoiceOut)
async def get_public_invoice(invoice_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.client), selectinload(Invoice.organization))
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    amount_paid = Decimal(str(inv.amount_paid or 0))
    balance_due = Decimal(str(inv.grand_total)) - amount_paid

    return PublicInvoiceOut(
        id=inv.id,
        business_name=inv.organization.name,
        client_name=inv.client.name,
        client_email=inv.client.email,
        grand_total=inv.grand_total,
        amount_paid=amount_paid,
        balance_due=balance_due,
        payment_status=inv.payment_status,
        due_date=inv.due_date,
        created_at=inv.created_at,
    )


@router.post("/{invoice_id}/mpesa")
async def public_mpesa_pay(
    invoice_id: str,
    payload: PublicMpesaRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id).options(selectinload(Invoice.organization))
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if inv.payment_status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice is already paid")

    balance_due = float(inv.grand_total) - float(inv.amount_paid or 0)
    charge = payload.amount if payload.amount else balance_due

    if charge <= 0 or charge > balance_due + 0.01:
        raise HTTPException(status_code=400, detail=f"Amount must be between 1 and {balance_due:.2f}")

    checkout_request_id = await initiate_stk_push(
        phone=payload.phone_number,
        amount=int(charge),
        account_ref=invoice_id,
        description=f"Payment for {invoice_id}",
        org=inv.organization,
    )
    inv.mpesa_checkout_request_id = checkout_request_id
    return {"message": "STK Push sent. Check your phone.", "checkout_request_id": checkout_request_id}
