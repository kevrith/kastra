import math
import uuid
from datetime import timedelta, timezone
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceItem
from app.models.organization import Organization
from app.models.quotation import Quotation, QuotationItem
from app.models.user import User
from app.schemas.common import MessageResponse, Meta, PaginatedResponse, Response
from app.schemas.quotation import QuotationCreate, QuotationListOut, QuotationOut, QuotationStatusUpdate, QuotationUpdate
from app.services.email_service import send_quotation_email
from app.utils.id_generator import next_id

router = APIRouter(prefix="/api/quotations", tags=["quotations"])

VAT_RATE = Decimal("0.16")

_load_full = selectinload(Quotation.client), selectinload(Quotation.items), selectinload(Quotation.created_by_user)


def _calculate_totals(items: list) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = sum(Decimal(str(i.quantity)) * Decimal(str(i.unit_price)) for i in items)
    taxable = sum(
        Decimal(str(i.quantity)) * Decimal(str(i.unit_price))
        for i in items if not getattr(i, "vat_exempt", False)
    )
    vat = (taxable * VAT_RATE).quantize(Decimal("0.01"))
    grand_total = subtotal + vat
    return subtotal, vat, grand_total


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
    subtotal, vat, grand_total = _calculate_totals(payload.items)

    quotation = Quotation(
        id=qt_id,
        organization_id=current_user.organization_id,
        client_id=payload.client_id,
        created_by=current_user.id,
        notes=payload.notes,
        expires_at=payload.expires_at,
        subtotal=subtotal,
        vat_amount=vat,
        grand_total=grand_total,
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
            vat_exempt=item.vat_exempt,
            sort_order=item.sort_order if item.sort_order else i,
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
        ).options(selectinload(Quotation.items))
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
    # Re-editing a declined quotation resets it to draft and clears the decline reason
    if qt.status == "declined":
        qt.status = "draft"
        qt.decline_reason = None

    if payload.items is not None:
        for old_item in qt.items:
            await db.delete(old_item)
        await db.flush()

        for i, item in enumerate(payload.items):
            line_total = Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
            db.add(QuotationItem(
                quotation_id=quotation_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=line_total,
                vat_exempt=item.vat_exempt,
                sort_order=item.sort_order if item.sort_order else i,
            ))
        subtotal, vat, grand_total = _calculate_totals(payload.items)
        qt.subtotal, qt.vat_amount, qt.grand_total = subtotal, vat, grand_total

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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.organization_id == current_user.organization_id,
        ).options(selectinload(Quotation.items))
    )
    qt = result.scalar_one_or_none()
    if not qt:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if qt.converted_to_invoice:
        raise HTTPException(status_code=400, detail="Already converted to invoice")
    if qt.status != "accepted":
        raise HTTPException(status_code=400, detail="Only accepted quotations can be converted")

    # Load org for payment terms
    await db.refresh(current_user, ["organization"])
    due_date = datetime.now(timezone.utc) + timedelta(days=current_user.organization.payment_terms_days)

    inv_id = await next_id(db, "invoice", current_user.organization_id)
    invoice = Invoice(
        id=inv_id,
        organization_id=current_user.organization_id,
        quotation_id=quotation_id,
        client_id=qt.client_id,
        subtotal=qt.subtotal,
        vat_amount=qt.vat_amount,
        grand_total=qt.grand_total,
        due_date=due_date,
    )
    db.add(invoice)

    for item in qt.items:
        db.add(InvoiceItem(
            invoice_id=inv_id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
            vat_exempt=item.vat_exempt,
            sort_order=item.sort_order,
        ))

    # Flush the invoice INSERT before updating the quotation's invoice_id FK
    # to avoid the flush-order violation (SQLAlchemy processes UPDATEs before INSERTs).
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
    """Send the quotation link to the client by email."""
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

    await send_quotation_email(
        client_email=qt.client.email,
        client_name=qt.client.name,
        quotation_id=qt.id,
        amount=float(qt.grand_total),
        business_name=org.name if org else "Business",
        expires_at=qt.expires_at.strftime("%d %b %Y") if qt.expires_at else None,
    )
    return MessageResponse(message="Quotation emailed to client")


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
