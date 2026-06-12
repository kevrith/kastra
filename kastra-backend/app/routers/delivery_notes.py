"""
Delivery notes — the goods-delivery document in the Kenyan B2B chain
(quotation → client LPO → delivery note → invoice). Generated from an
invoice or quotation (items copied, no prices shown) or standalone.
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
from app.models.delivery_note import DeliveryNote, DeliveryNoteItem
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.quotation import Quotation
from app.models.user import User
from app.schemas.common import MessageResponse, Meta, PaginatedResponse, Response
from app.schemas.delivery_note import DeliveryNoteCreate, DeliveryNoteOut, DeliveryNoteUpdate
from app.schemas.organization import OrganizationOut
from app.services.pdf_service import generate_delivery_note_pdf
from app.utils.id_generator import next_id

router = APIRouter(prefix="/api/delivery-notes", tags=["delivery-notes"])

_load_full = (
    selectinload(DeliveryNote.items),
    selectinload(DeliveryNote.client),
)


async def _get_dn(db: AsyncSession, delivery_note_id: str, org_id) -> DeliveryNote:
    dn = (await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == delivery_note_id, DeliveryNote.organization_id == org_id)
        .options(*_load_full)
    )).scalar_one_or_none()
    if not dn:
        raise HTTPException(status_code=404, detail="Delivery note not found")
    return dn


@router.get("", response_model=PaginatedResponse[DeliveryNoteOut])
async def list_delivery_notes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    invoice_id: str | None = Query(None),
    quotation_id: str | None = Query(None),
    client_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
):
    q = select(DeliveryNote).options(selectinload(DeliveryNote.items)).where(
        DeliveryNote.organization_id == current_user.organization_id
    )
    if invoice_id:
        q = q.where(DeliveryNote.invoice_id == invoice_id)
    if quotation_id:
        q = q.where(DeliveryNote.quotation_id == quotation_id)
    if client_id:
        q = q.where(DeliveryNote.client_id == client_id)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(DeliveryNote.created_at.desc()).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return PaginatedResponse(
        data=rows,
        meta=Meta(page=page, limit=limit, total=total, pages=math.ceil(total / limit)),
    )


@router.post("", response_model=Response[DeliveryNoteOut], status_code=status.HTTP_201_CREATED)
async def create_delivery_note(
    payload: DeliveryNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_edit_invoices")),
):
    org_id = current_user.organization_id
    client_id = payload.client_id
    lpo_number = payload.lpo_number
    source_items: list[tuple[str, Decimal]] = []

    if payload.invoice_id:
        inv = (await db.execute(
            select(Invoice)
            .where(Invoice.id == payload.invoice_id, Invoice.organization_id == org_id)
            .options(selectinload(Invoice.items))
        )).scalar_one_or_none()
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")
        client_id = inv.client_id
        lpo_number = lpo_number or inv.lpo_number
        source_items = [(i.description, i.quantity) for i in inv.items]
    elif payload.quotation_id:
        qt = (await db.execute(
            select(Quotation)
            .where(Quotation.id == payload.quotation_id, Quotation.organization_id == org_id)
            .options(selectinload(Quotation.items))
        )).scalar_one_or_none()
        if not qt:
            raise HTTPException(status_code=404, detail="Quotation not found")
        client_id = qt.client_id
        source_items = [(i.description, i.quantity) for i in qt.items]

    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required when no invoice or quotation is given")

    items = payload.items
    if not items and not source_items:
        raise HTTPException(status_code=400, detail="At least one item is required")

    dn_id = await next_id(db, "delivery_note", org_id)
    dn = DeliveryNote(
        id=dn_id,
        organization_id=org_id,
        invoice_id=payload.invoice_id,
        quotation_id=payload.quotation_id,
        client_id=client_id,
        lpo_number=lpo_number,
        delivery_date=payload.delivery_date,
        vehicle_reg=payload.vehicle_reg,
        driver_name=payload.driver_name,
        notes=payload.notes,
    )
    db.add(dn)

    if items:
        for idx, item in enumerate(items):
            db.add(DeliveryNoteItem(
                delivery_note_id=dn_id,
                description=item.description,
                quantity=item.quantity,
                unit=item.unit,
                sort_order=idx,
            ))
    else:
        for idx, (description, quantity) in enumerate(source_items):
            db.add(DeliveryNoteItem(
                delivery_note_id=dn_id,
                description=description,
                quantity=quantity,
                sort_order=idx,
            ))

    await db.flush()
    dn = await _get_dn(db, dn_id, org_id)
    return Response(data=dn)


@router.get("/{delivery_note_id}", response_model=Response[DeliveryNoteOut])
async def get_delivery_note(
    delivery_note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
):
    dn = await _get_dn(db, delivery_note_id, current_user.organization_id)
    return Response(data=dn)


@router.patch("/{delivery_note_id}", response_model=Response[DeliveryNoteOut])
async def update_delivery_note(
    delivery_note_id: str,
    payload: DeliveryNoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_edit_invoices")),
):
    dn = await _get_dn(db, delivery_note_id, current_user.organization_id)
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in ("issued", "delivered"):
        raise HTTPException(status_code=400, detail="status must be 'issued' or 'delivered'")
    for field, value in updates.items():
        setattr(dn, field, value)
    await db.flush()
    return Response(data=dn)


@router.get("/{delivery_note_id}/pdf")
async def download_delivery_note_pdf(
    delivery_note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_invoices")),
):
    dn = await _get_dn(db, delivery_note_id, current_user.organization_id)
    org = (await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )).scalar_one()

    doc = DeliveryNoteOut.model_validate(dn).model_dump(mode="json")
    doc["client"] = {"name": dn.client.name, "email": dn.client.email, "phone": dn.client.phone, "address": dn.client.address}
    org_data = OrganizationOut.model_validate(org).model_dump(mode="json")

    pdf_bytes = await generate_delivery_note_pdf(doc, org_data)
    return RawResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{delivery_note_id}.pdf"'},
    )


@router.delete("/{delivery_note_id}", response_model=MessageResponse)
async def delete_delivery_note(
    delivery_note_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_delete_invoices")),
):
    dn = await _get_dn(db, delivery_note_id, current_user.organization_id)
    await db.delete(dn)
    return MessageResponse(message="Delivery note deleted")
