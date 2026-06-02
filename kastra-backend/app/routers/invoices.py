import asyncio
import logging
import math
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import and_

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response as RawResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.client import Client
from app.models.client_price import ClientPrice
from app.models.expense import Expense
from app.models.invoice import Invoice, InvoiceCharge, InvoiceItem, PaymentDetail
from app.models.organization import Organization
from app.models.product import Product
from app.models.user import User
from app.schemas.common import MessageResponse, Meta, PaginatedResponse, Response
from app.schemas.invoice import EtimsSubmitRequest, InvoiceCreate, InvoiceExpenseOut, InvoiceListOut, InvoiceOut, MarkPaidRequest, MpesaPayRequest
from app.schemas.organization import OrganizationOut
from app.services.email_service import send_invoice_email
from app.services.etims_service import submit_to_kra, verification_url
from app.services.mpesa_service import initiate_stk_push
from app.services.pdf_service import generate_pdf
from app.services.sms_service import sms_invoice_sent
from app.utils.id_generator import next_id
from app.utils.plan_limits import get_limits
from app.utils.totals import calculate_totals

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

VAT_RATE = Decimal("0.16")


def _maybe_reset_counters(org) -> None:
    """Reset monthly counters if we've rolled into a new billing month."""
    now = datetime.now(timezone.utc)
    reset_at = org.counters_reset_at
    if reset_at is None or (now.year > reset_at.year or now.month > reset_at.month):
        org.invoices_this_month = 0
        org.quotations_this_month = 0
        org.ocr_scans_this_month = 0
        org.counters_reset_at = now


async def _upsert_client_price(db: AsyncSession, org_id, client_id, description: str, unit_price: Decimal):
    stmt = pg_insert(ClientPrice).values(
        organization_id=org_id,
        client_id=client_id,
        description=description,
        unit_price=unit_price,
    ).on_conflict_do_update(
        index_elements=["organization_id", "client_id", "description"],
        set_={"unit_price": unit_price},
    )
    await db.execute(stmt)


async def _upsert_product(db: AsyncSession, org_id, description: str, unit_price: Decimal, cost_price: Decimal | None = None):
    values = dict(id=uuid.uuid4(), organization_id=org_id, name=description, unit_price=unit_price)
    update_set: dict = {"unit_price": unit_price}
    if cost_price is not None and cost_price > 0:
        values["cost_price"] = cost_price
        update_set["cost_price"] = cost_price
    stmt = pg_insert(Product).values(**values).on_conflict_do_update(
        index_elements=["organization_id", "name"],
        set_=update_set,
    )
    await db.execute(stmt)


_load_full = (
    selectinload(Invoice.client),
    selectinload(Invoice.items),
    selectinload(Invoice.charges),
    selectinload(Invoice.payment_detail),
    selectinload(Invoice.expenses),
)


@router.get("", response_model=PaginatedResponse[InvoiceListOut])
async def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    payment_status: str | None = Query(None),
    client_id: uuid.UUID | None = Query(None),
    quotation_id: str | None = Query(None),
    overdue: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
):
    q = select(Invoice).options(selectinload(Invoice.client)).where(
        Invoice.organization_id == current_user.organization_id
    )
    if payment_status:
        q = q.where(Invoice.payment_status == payment_status)
    if client_id:
        q = q.where(Invoice.client_id == client_id)
    if quotation_id:
        q = q.where(Invoice.quotation_id == quotation_id)
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


@router.post("", response_model=Response[InvoiceOut], status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_create_invoices")),
):
    client = await db.get(Client, payload.client_id)
    if not client or client.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Client not found")

    org_result = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = org_result.scalar_one_or_none()

    # Enforce plan invoice limit
    if org:
        limits = get_limits(org.plan)
        _maybe_reset_counters(org)
        cap = limits["invoices_per_month"]
        if cap != -1 and org.invoices_this_month >= cap:
            raise HTTPException(
                status_code=402,
                detail=f"Invoice limit reached ({cap}/month on {org.plan} plan). Upgrade to create more.",
            )

    due_date = payload.due_date
    if due_date is None and org:
        due_date = datetime.now(timezone.utc) + timedelta(days=org.payment_terms_days)

    totals = calculate_totals(payload.items, payload.charges, payload.discount_pct, payload.wht_pct)

    inv_id = await next_id(db, "invoice", current_user.organization_id)
    invoice = Invoice(
        id=inv_id,
        organization_id=current_user.organization_id,
        client_id=payload.client_id,
        lpo_number=payload.lpo_number,
        invoice_date=payload.invoice_date,
        discount_pct=payload.discount_pct,
        wht_pct=payload.wht_pct,
        deposit_amount=payload.deposit_amount,
        due_date=due_date,
        **totals,
    )
    db.add(invoice)

    for i, item in enumerate(payload.items):
        line_total = Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
        db.add(InvoiceItem(
            invoice_id=inv_id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            cost_price=item.cost_price,
            line_total=line_total,
            discount_pct=item.discount_pct,
            vat_exempt=item.vat_exempt,
            sort_order=item.sort_order if item.sort_order else i,
        ))
        await _upsert_product(db, current_user.organization_id, item.description, Decimal(str(item.unit_price)), item.cost_price)
        await _upsert_client_price(db, current_user.organization_id, payload.client_id, item.description, Decimal(str(item.unit_price)))

    for i, charge in enumerate(payload.charges):
        db.add(InvoiceCharge(
            invoice_id=inv_id,
            description=charge.description,
            amount=charge.amount,
            vat_exempt=charge.vat_exempt,
            sort_order=charge.sort_order if charge.sort_order else i,
        ))

    if org:
        org.invoices_this_month += 1

    await db.flush()
    result = await db.execute(
        select(Invoice).where(Invoice.id == inv_id).options(*_load_full)
    )
    return Response(data=result.scalar_one())


@router.get("/{invoice_id}", response_model=Response[InvoiceOut])
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
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
    current_user: User = Depends(require_permission("can_edit_invoices")),
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
    current_user: User = Depends(require_permission("can_view_invoices")),
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
    current_user: User = Depends(require_permission("can_edit_invoices")),
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
        await submit_to_kra(db, invoice_id, org)
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
    current_user: User = Depends(require_permission("can_edit_invoices")),
):
    """Send the invoice to the client by email with a PDF attachment."""
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == current_user.organization_id,
        ).options(selectinload(Invoice.client), selectinload(Invoice.organization), selectinload(Invoice.items))
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not inv.client or not inv.client.email:
        raise HTTPException(status_code=400, detail="Client has no email address")

    org_res = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = org_res.scalar_one_or_none()
    biz_name = org.name if org else "Business"

    doc = InvoiceOut.model_validate(inv).model_dump(mode="json")
    org_data = OrganizationOut.model_validate(org).model_dump(mode="json") if org else {}
    try:
        pdf_bytes = await generate_pdf("invoice", doc, org_data)
    except Exception:
        logger.exception("PDF generation failed for invoice email %s", inv.id)
        pdf_bytes = None

    await send_invoice_email(
        client_email=inv.client.email,
        client_name=inv.client.name,
        invoice_id=inv.id,
        amount=float(inv.grand_total),
        business_name=biz_name,
        due_date=inv.due_date.strftime("%d %b %Y") if inv.due_date else None,
        pdf_bytes=pdf_bytes,
    )
    asyncio.ensure_future(sms_invoice_sent(
        client_phone=inv.client.phone if inv.client else None,
        client_name=inv.client.name,
        invoice_id=inv.id,
        amount=float(inv.grand_total),
        business_name=biz_name,
    ))
    return MessageResponse(message="Invoice emailed to client")


@router.post("/{invoice_id}/remind", response_model=MessageResponse)
async def send_reminder(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
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


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
):
    """Generate and return invoice as a PDF file."""
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == current_user.organization_id,
        ).options(*_load_full)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    org_result = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = org_result.scalar_one_or_none()

    doc = InvoiceOut.model_validate(inv).model_dump(mode="json")
    org_data = OrganizationOut.model_validate(org).model_dump(mode="json") if org else {}

    pdf_bytes = await generate_pdf("invoice", doc, org_data)
    return RawResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice_id}.pdf"'},
    )


# ── Invoice-scoped Job Expenses ──────────────────────────────────────────────

from datetime import date as _date
from pydantic import BaseModel as _BaseModel

JOB_EXPENSE_CATEGORIES = [
    "materials", "labour", "lunch", "transport", "fuel",
    "rent", "salaries", "utilities", "supplies", "marketing", "other",
]


class JobExpenseIn(_BaseModel):
    category: str
    description: str
    vendor: str | None = None
    amount: float
    date: _date


@router.get("/{invoice_id}/expenses", response_model=list[InvoiceExpenseOut])
async def list_invoice_expenses(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
):
    inv = await db.get(Invoice, invoice_id)
    if not inv or inv.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    rows = (await db.execute(
        select(Expense).where(Expense.invoice_id == invoice_id).order_by(Expense.date)
    )).scalars().all()
    return rows


@router.post("/{invoice_id}/expenses", response_model=InvoiceExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_invoice_expense(
    invoice_id: str,
    payload: JobExpenseIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_create_expenses")),
):
    inv = await db.get(Invoice, invoice_id)
    if not inv or inv.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    exp = Expense(
        organization_id=current_user.organization_id,
        invoice_id=invoice_id,
        category=payload.category,
        description=payload.description,
        vendor=payload.vendor,
        amount=payload.amount,
        date=payload.date,
    )
    db.add(exp)
    await db.flush()
    await db.refresh(exp)
    return exp


@router.put("/{invoice_id}/expenses/{expense_id}", response_model=InvoiceExpenseOut)
async def update_invoice_expense(
    invoice_id: str,
    expense_id: uuid.UUID,
    payload: JobExpenseIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_create_expenses")),
):
    exp = await db.get(Expense, expense_id)
    if not exp or exp.invoice_id != invoice_id or exp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Expense not found")
    exp.category = payload.category
    exp.description = payload.description
    exp.vendor = payload.vendor
    exp.amount = payload.amount
    exp.date = payload.date
    await db.flush()
    await db.refresh(exp)
    return exp


@router.delete("/{invoice_id}/expenses/{expense_id}", response_model=MessageResponse)
async def delete_invoice_expense(
    invoice_id: str,
    expense_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_create_expenses")),
):
    exp = await db.get(Expense, expense_id)
    if not exp or exp.invoice_id != invoice_id or exp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Expense not found")
    await db.delete(exp)
    return MessageResponse(message="Expense deleted")
