import math
import uuid
from datetime import datetime, timezone
from sqlalchemy import and_

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.invoice import Invoice, PaymentDetail
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import MessageResponse, Meta, PaginatedResponse, Response
from app.schemas.invoice import EtimsSubmitRequest, InvoiceListOut, InvoiceOut, MarkPaidRequest, MpesaPayRequest
from app.config import settings
from app.services.email_service import send_invoice_email
from app.services.etims_service import submit_to_kra, verification_url
from app.services.mpesa_service import initiate_stk_push

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

_load_full = (
    selectinload(Invoice.client),
    selectinload(Invoice.items),
    selectinload(Invoice.payment_detail),
)


@router.get("", response_model=PaginatedResponse[InvoiceListOut])
async def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    payment_status: str | None = Query(None),
    client_id: uuid.UUID | None = Query(None),
    overdue: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Invoice).options(selectinload(Invoice.client)).where(
        Invoice.organization_id == current_user.organization_id
    )
    if payment_status:
        q = q.where(Invoice.payment_status == payment_status)
    if client_id:
        q = q.where(Invoice.client_id == client_id)
    if overdue is True:
        q = q.where(and_(
            Invoice.payment_status == "unpaid",
            Invoice.due_date.isnot(None),
            Invoice.due_date < datetime.now(timezone.utc),
        ))

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(Invoice.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    rows = result.scalars().all()

    return PaginatedResponse(
        data=rows,
        meta=Meta(page=page, limit=limit, total=total, pages=math.ceil(total / limit)),
    )


@router.get("/{invoice_id}", response_model=Response[InvoiceOut])
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == current_user.organization_id,
        ).options(*_load_full)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return Response(data=inv)


@router.patch("/{invoice_id}/mark-paid", response_model=Response[InvoiceOut])
async def mark_paid(
    invoice_id: str,
    payload: MarkPaidRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == current_user.organization_id,
        ).options(*_load_full)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already marked as paid")

    inv.payment_status = "paid"
    inv.payment_method = payload.payment_method

    payment = PaymentDetail(
        invoice_id=invoice_id,
        payment_method=payload.payment_method,
        payment_date=payload.payment_date,
        mpesa_receipt_number=payload.mpesa_receipt_number,
        transaction_id=payload.transaction_id,
        notes=payload.notes,
    )
    db.add(payment)
    await db.flush()
    db.expire(inv)

    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id).options(*_load_full)
    )
    return Response(data=result.scalar_one())


@router.post("/{invoice_id}/mpesa-pay")
async def mpesa_pay(
    invoice_id: str,
    payload: MpesaPayRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == current_user.organization_id,
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already paid")

    checkout_request_id = await initiate_stk_push(
        phone=payload.phone_number,
        amount=int(inv.grand_total),
        account_ref=invoice_id,
        description=f"Payment for {invoice_id}",
    )
    inv.mpesa_checkout_request_id = checkout_request_id
    return {"message": "STK Push sent. Check your phone.", "checkout_request_id": checkout_request_id}


@router.post("/{invoice_id}/etims-submit", response_model=Response[InvoiceOut])
async def etims_submit(
    invoice_id: str,
    _: EtimsSubmitRequest = EtimsSubmitRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit invoice to KRA eTIMS and get back a Control Unit Invoice Number."""
    org_result = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not org.etims_enabled:
        raise HTTPException(status_code=400, detail="eTIMS is not enabled for this business. Enable it in Settings.")
    if not org.etims_device_serial or not org.etims_auth_token:
        raise HTTPException(status_code=400, detail="eTIMS credentials incomplete. Add Device Serial and Auth Token in Settings.")

    try:
        inv = await submit_to_kra(db, invoice_id, org)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id).options(*_load_full)
    )
    return Response(data=result.scalar_one())


@router.post("/{invoice_id}/email", response_model=MessageResponse)
async def email_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send the invoice to the client by email."""
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == current_user.organization_id,
        ).options(selectinload(Invoice.client), selectinload(Invoice.organization))
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not inv.client or not inv.client.email:
        raise HTTPException(status_code=400, detail="Client has no email address")

    from app.models.organization import Organization
    org_res = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = org_res.scalar_one_or_none()

    await send_invoice_email(
        client_email=inv.client.email,
        client_name=inv.client.name,
        invoice_id=inv.id,
        amount=float(inv.grand_total),
        business_name=org.name if org else "Business",
        due_date=inv.due_date.strftime("%d %b %Y") if inv.due_date else None,
    )
    return MessageResponse(message="Invoice emailed to client")


@router.post("/{invoice_id}/remind", response_model=MessageResponse)
async def send_reminder(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == current_user.organization_id,
        ).options(selectinload(Invoice.client))
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    phone = inv.client.phone or ""
    pay_link = f"{settings.frontend_url}/pay/{invoice_id}"
    message = (
        f"Hello {inv.client.name}, this is a reminder that invoice *{invoice_id}* "
        f"for *KSh {inv.grand_total:,.2f}* is due.\n\n"
        f"Pay online here: {pay_link}\n\nThank you."
    )
    whatsapp_url = f"https://wa.me/{phone}?text={message}"
    inv.reminders_sent += 1

    return MessageResponse(message=whatsapp_url)
