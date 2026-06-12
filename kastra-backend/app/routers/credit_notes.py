"""
Credit notes — the KRA-compliant way to correct or reverse an issued invoice.
An eTIMS-submitted invoice cannot be edited or deleted; a credit note records
the reversal, reduces the invoice balance, and can itself be submitted to
eTIMS as a refund receipt.
"""
import math
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response as RawResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_permission
from app.models.credit_note import CreditNote, CreditNoteItem
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import MessageResponse, Meta, PaginatedResponse, Response
from app.schemas.credit_note import CreditNoteCreate, CreditNoteListOut, CreditNoteOut
from app.schemas.organization import OrganizationOut
from app.services.etims_service import submit_credit_note_to_kra
from app.services.pdf_service import generate_credit_note_pdf
from app.utils.id_generator import next_id
from app.utils.totals import calculate_totals

router = APIRouter(prefix="/api/credit-notes", tags=["credit-notes"])

_load_full = (
    selectinload(CreditNote.items),
    selectinload(CreditNote.client),
)


async def _get_cn(db: AsyncSession, credit_note_id: str, org_id) -> CreditNote:
    cn = (await db.execute(
        select(CreditNote)
        .where(CreditNote.id == credit_note_id, CreditNote.organization_id == org_id)
        .options(*_load_full)
    )).scalar_one_or_none()
    if not cn:
        raise HTTPException(status_code=404, detail="Credit note not found")
    return cn


@router.get("", response_model=PaginatedResponse[CreditNoteListOut])
async def list_credit_notes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    invoice_id: str | None = Query(None),
    client_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
):
    q = select(CreditNote).where(CreditNote.organization_id == current_user.organization_id)
    if invoice_id:
        q = q.where(CreditNote.invoice_id == invoice_id)
    if client_id:
        q = q.where(CreditNote.client_id == client_id)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(CreditNote.created_at.desc()).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return PaginatedResponse(
        data=rows,
        meta=Meta(page=page, limit=limit, total=total, pages=math.ceil(total / limit)),
    )


@router.post("", response_model=Response[CreditNoteOut], status_code=status.HTTP_201_CREATED)
async def create_credit_note(
    payload: CreditNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_edit_invoices")),
):
    inv = (await db.execute(
        select(Invoice).where(
            Invoice.id == payload.invoice_id,
            Invoice.organization_id == current_user.organization_id,
        )
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    totals = calculate_totals(payload.items)
    grand_total = totals["grand_total"]
    if grand_total <= 0:
        raise HTTPException(status_code=400, detail="Credit note total must be positive")

    already_credited = Decimal(str(inv.amount_credited or 0))
    creditable = Decimal(str(inv.grand_total)) - already_credited
    if grand_total > creditable + Decimal("0.01"):
        raise HTTPException(
            status_code=400,
            detail=f"Credit note exceeds creditable amount of {creditable:,.2f} on this invoice",
        )

    cn_id = await next_id(db, "credit_note", current_user.organization_id)
    cn = CreditNote(
        id=cn_id,
        organization_id=current_user.organization_id,
        invoice_id=inv.id,
        client_id=inv.client_id,
        reason=payload.reason,
        currency=inv.currency,
        exchange_rate=inv.exchange_rate,
        subtotal=totals["subtotal"],
        vat_amount=totals["vat_amount"],
        grand_total=grand_total,
    )
    db.add(cn)
    for idx, item in enumerate(payload.items):
        db.add(CreditNoteItem(
            credit_note_id=cn_id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=(item.quantity * item.unit_price).quantize(Decimal("0.01")),
            vat_exempt=item.vat_exempt,
            sort_order=idx,
        ))

    # Apply the credit to the invoice balance
    inv.amount_credited = already_credited + grand_total
    paid = Decimal(str(inv.amount_paid or 0))
    if paid + inv.amount_credited >= Decimal(str(inv.grand_total)):
        inv.payment_status = "paid"
    elif paid + inv.amount_credited > 0:
        inv.payment_status = "partial"

    await db.flush()
    cn = await _get_cn(db, cn_id, current_user.organization_id)
    return Response(data=cn)


@router.get("/{credit_note_id}", response_model=Response[CreditNoteOut])
async def get_credit_note(
    credit_note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
):
    cn = await _get_cn(db, credit_note_id, current_user.organization_id)
    return Response(data=cn)


@router.post("/{credit_note_id}/etims", response_model=Response[CreditNoteOut])
async def etims_submit_credit_note(
    credit_note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_edit_invoices")),
):
    cn = await _get_cn(db, credit_note_id, current_user.organization_id)
    org = (await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )).scalar_one()
    if not org.etims_enabled:
        raise HTTPException(status_code=400, detail="eTIMS is not enabled for this organisation")
    try:
        await submit_credit_note_to_kra(db, cn, org)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(data=cn)


@router.get("/{credit_note_id}/pdf")
async def download_credit_note_pdf(
    credit_note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
):
    cn = await _get_cn(db, credit_note_id, current_user.organization_id)
    org = (await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )).scalar_one()

    doc = CreditNoteOut.model_validate(cn).model_dump(mode="json")
    doc["client"] = {"name": cn.client.name, "email": cn.client.email, "phone": cn.client.phone, "address": cn.client.address}
    org_data = OrganizationOut.model_validate(org).model_dump(mode="json")

    pdf_bytes = await generate_credit_note_pdf(doc, org_data)
    return RawResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{credit_note_id}.pdf"'},
    )


@router.delete("/{credit_note_id}", response_model=MessageResponse)
async def void_credit_note(
    credit_note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_delete_invoices")),
):
    """Void a credit note and restore the invoice balance. Not allowed once submitted to eTIMS."""
    cn = await _get_cn(db, credit_note_id, current_user.organization_id)
    if cn.etims_cu_invoice_no:
        raise HTTPException(status_code=400, detail="Cannot void a credit note already submitted to eTIMS")

    inv = (await db.execute(
        select(Invoice).where(Invoice.id == cn.invoice_id)
    )).scalar_one_or_none()
    if inv:
        inv.amount_credited = max(
            Decimal("0"), Decimal(str(inv.amount_credited or 0)) - Decimal(str(cn.grand_total))
        )
        paid = Decimal(str(inv.amount_paid or 0))
        covered = paid + Decimal(str(inv.amount_credited))
        if covered >= Decimal(str(inv.grand_total)):
            inv.payment_status = "paid"
        elif covered > 0:
            inv.payment_status = "partial"
        else:
            inv.payment_status = "unpaid"

    await db.delete(cn)
    return MessageResponse(message="Credit note voided")
