import logging
import math
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.dialects.postgresql import insert as pg_insert

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response as RawResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.client_price import ClientPrice
from app.models.invoice import Invoice, InvoiceCharge, InvoiceItem
from app.models.organization import Organization
from app.models.quotation import Quotation, QuotationCharge, QuotationItem
from app.models.user import User
from app.schemas.common import MessageResponse, Meta, PaginatedResponse, Response
from app.schemas.organization import OrganizationOut
from app.schemas.quotation import ConvertRequest, QuotationCreate, QuotationListOut, QuotationOut, QuotationStatusUpdate, QuotationUpdate
from app.services.email_service import send_quotation_email
from app.services.pdf_service import generate_pdf
from app.utils.id_generator import next_id
from app.utils.totals import calculate_totals

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quotations", tags=["quotations"])

VAT_RATE = Decimal("0.16")

_load_full = (
    selectinload(Quotation.client),
    selectinload(Quotation.items),
    selectinload(Quotation.charges),
    selectinload(Quotation.created_by_user),
)


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




@router.get("", response_model=PaginatedResponse[QuotationListOut])
async def list_quotations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    client_id: uuid.UUID | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Quotation).options(selectinload(Quotation.client)).where(
        Quotation.organization_id == current_user.organization_id
    )
    if status:
        q = q.where(Quotation.status == status)
    if client_id:
        q = q.where(Quotation.client_id == client_id)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(Quotation.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    rows = result.scalars().all()

    return PaginatedResponse(
        data=rows,
        meta=Meta(page=page, limit=limit, total=total, pages=math.ceil(total / limit)),
    )


@router.post("", response_model=Response[QuotationOut], status_code=status.HTTP_201_CREATED)
async def create_quotation(
    payload: QuotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = await db.get(Client, payload.client_id)
    if not client or client.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Client not found")

    qt_id = await next_id(db, "quotation", current_user.organization_id)
    totals = calculate_totals(payload.items, payload.charges, payload.discount_pct, payload.wht_pct)

    quotation = Quotation(
        id=qt_id,
        organization_id=current_user.organization_id,
        client_id=payload.client_id,
        created_by=current_user.id,
        notes=payload.notes,
        expires_at=payload.expires_at,
        discount_pct=payload.discount_pct,
        wht_pct=payload.wht_pct,
        **totals,
    )
    db.add(quotation)

    for i, item in enumerate(payload.items):
        line_total = Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
        db.add(QuotationItem(
            quotation_id=qt_id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=line_total,
            discount_pct=item.discount_pct,
            vat_exempt=item.vat_exempt,
            sort_order=item.sort_order if item.sort_order else i,
        ))
        await _upsert_client_price(db, current_user.organization_id, payload.client_id, item.description, Decimal(str(item.unit_price)))

    for i, charge in enumerate(payload.charges):
        db.add(QuotationCharge(
            quotation_id=qt_id,
            description=charge.description,
            amount=charge.amount,
            vat_exempt=charge.vat_exempt,
            sort_order=charge.sort_order if charge.sort_order else i,
        ))

    await db.flush()
    result = await db.execute(
        select(Quotation).where(Quotation.id == qt_id).options(*_load_full)
    )
    return Response(data=result.scalar_one())


@router.get("/{quotation_id}", response_model=Response[QuotationOut])
async def get_quotation(
    quotation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.organization_id == current_user.organization_id,
        ).options(*_load_full)
    )
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return Response(data=qt)


@router.put("/{quotation_id}", response_model=Response[QuotationOut])
async def update_quotation(
    quotation_id: str,
    payload: QuotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.organization_id == current_user.organization_id,
        ).options(selectinload(Quotation.items), selectinload(Quotation.charges))
    )
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if qt.status not in ("draft", "pending", "declined"):
        raise HTTPException(status_code=400, detail="Cannot edit an accepted or converted quotation")

    if payload.client_id:
        qt.client_id = payload.client_id
    if payload.notes is not None:
        qt.notes = payload.notes
    if payload.expires_at is not None:
        qt.expires_at = payload.expires_at
    if payload.discount_pct is not None:
        qt.discount_pct = payload.discount_pct
    if payload.wht_pct is not None:
        qt.wht_pct = payload.wht_pct
    if qt.status == "declined":
        qt.status = "draft"
        qt.decline_reason = None

    # Determine current items/charges for recalculation
    new_items = payload.items
    new_charges = payload.charges

    if new_items is not None:
        for old_item in qt.items:
            await db.delete(old_item)
        await db.flush()
        for i, item in enumerate(new_items):
            line_total = Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
            db.add(QuotationItem(
                quotation_id=quotation_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=line_total,
                discount_pct=item.discount_pct,
                vat_exempt=item.vat_exempt,
                sort_order=item.sort_order if item.sort_order else i,
            ))

    if new_charges is not None:
        for old_charge in qt.charges:
            await db.delete(old_charge)
        await db.flush()
        for i, charge in enumerate(new_charges):
            db.add(QuotationCharge(
                quotation_id=quotation_id,
                description=charge.description,
                amount=charge.amount,
                vat_exempt=charge.vat_exempt,
                sort_order=charge.sort_order if charge.sort_order else i,
            ))

    if new_items is not None or new_charges is not None:
        items_for_calc = new_items if new_items is not None else qt.items
        charges_for_calc = new_charges if new_charges is not None else qt.charges
        totals = calculate_totals(items_for_calc, charges_for_calc, qt.discount_pct, qt.wht_pct)
        for k, v in totals.items():
            setattr(qt, k, v)

    await db.flush()
    db.expire(qt)
    result = await db.execute(
        select(Quotation).where(Quotation.id == quotation_id).options(*_load_full)
    )
    return Response(data=result.scalar_one())


@router.patch("/{quotation_id}/status", response_model=Response[QuotationOut])
async def update_status(
    quotation_id: str,
    payload: QuotationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.organization_id == current_user.organization_id,
        ).options(*_load_full)
    )
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    qt.status = payload.status
    await db.flush()
    await db.refresh(qt)
    return Response(data=qt)


@router.post("/{quotation_id}/convert", response_model=Response[QuotationOut])
async def convert_to_invoice(
    quotation_id: str,
    payload: ConvertRequest = ConvertRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.organization_id == current_user.organization_id,
        ).options(selectinload(Quotation.items), selectinload(Quotation.charges))
    )
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if qt.status != "accepted":
        raise HTTPException(status_code=400, detail="Only accepted quotations can be converted")

    await db.refresh(current_user, ["organization"])
    due_date = datetime.now(timezone.utc) + timedelta(days=current_user.organization.payment_terms_days)

    qty_override = {o.sort_order: Decimal(str(o.quantity)) for o in payload.item_quantities} if payload.item_quantities else {}

    class _EffectiveItem:
        def __init__(self, item, qty):
            self.quantity = qty
            self.unit_price = item.unit_price
            self.discount_pct = item.discount_pct
            self.vat_exempt = item.vat_exempt

    effective_items = [_EffectiveItem(item, qty_override.get(item.sort_order, Decimal(str(item.quantity)))) for item in qt.items]
    totals = calculate_totals(effective_items, qt.charges, qt.discount_pct, qt.wht_pct)

    inv_id = await next_id(db, "invoice", current_user.organization_id)
    invoice = Invoice(
        id=inv_id,
        organization_id=current_user.organization_id,
        quotation_id=quotation_id,
        client_id=qt.client_id,
        lpo_number=payload.lpo_number,
        discount_pct=qt.discount_pct,
        wht_pct=qt.wht_pct,
        due_date=due_date,
        **totals,
    )
    db.add(invoice)

    for item in qt.items:
        effective_qty = qty_override.get(item.sort_order, Decimal(str(item.quantity)))
        line_total = effective_qty * Decimal(str(item.unit_price))
        db.add(InvoiceItem(
            invoice_id=inv_id,
            description=item.description,
            quantity=effective_qty,
            unit_price=item.unit_price,
            line_total=line_total,
            discount_pct=item.discount_pct,
            vat_exempt=item.vat_exempt,
            sort_order=item.sort_order,
        ))
        await _upsert_client_price(db, current_user.organization_id, qt.client_id, item.description, Decimal(str(item.unit_price)))

    for charge in qt.charges:
        db.add(InvoiceCharge(
            invoice_id=inv_id,
            description=charge.description,
            amount=charge.amount,
            vat_exempt=charge.vat_exempt,
            sort_order=charge.sort_order,
        ))

    # Flush the invoice INSERT before updating the quotation's invoice_id FK
    await db.flush()

    qt.converted_to_invoice = True
    qt.invoice_id = inv_id
    await db.flush()

    result = await db.execute(
        select(Quotation).where(Quotation.id == quotation_id).options(*_load_full)
    )
    return Response(data=result.scalar_one())


@router.post("/{quotation_id}/email", response_model=MessageResponse)
async def email_quotation(
    quotation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send the quotation to the client by email with a PDF attachment."""
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.organization_id == current_user.organization_id,
        ).options(*_load_full)
    )
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if not qt.client or not qt.client.email:
        raise HTTPException(status_code=400, detail="Client has no email address")

    org_res = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = org_res.scalar_one_or_none()

    doc = QuotationOut.model_validate(qt).model_dump(mode="json")
    org_data = OrganizationOut.model_validate(org).model_dump(mode="json") if org else {}
    try:
        pdf_bytes = await generate_pdf("quotation", doc, org_data)
    except Exception:
        logger.exception("PDF generation failed for quotation email %s", qt.id)
        pdf_bytes = None

    await send_quotation_email(
        client_email=qt.client.email,
        client_name=qt.client.name,
        quotation_id=qt.id,
        amount=float(qt.grand_total),
        business_name=org.name if org else "Business",
        expires_at=qt.expires_at.strftime("%d %b %Y") if qt.expires_at else None,
        pdf_bytes=pdf_bytes,
    )
    return MessageResponse(message="Quotation emailed to client")


@router.get("/{quotation_id}/pdf")
async def download_quotation_pdf(
    quotation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and return quotation as a PDF file."""
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.organization_id == current_user.organization_id,
        ).options(*_load_full)
    )
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")

    org_res = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = org_res.scalar_one_or_none()

    doc = QuotationOut.model_validate(qt).model_dump(mode="json")
    org_data = OrganizationOut.model_validate(org).model_dump(mode="json") if org else {}

    pdf_bytes = await generate_pdf("quotation", doc, org_data)
    return RawResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quotation_id}.pdf"'},
    )


@router.delete("/{quotation_id}", response_model=MessageResponse)
async def delete_quotation(
    quotation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.organization_id == current_user.organization_id,
        )
    )
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if qt.converted_to_invoice:
        raise HTTPException(status_code=400, detail="Cannot delete a converted quotation")
    await db.delete(qt)
    return MessageResponse(message="Quotation deleted")
