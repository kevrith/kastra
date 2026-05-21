"""
Recurring invoices — create a template that auto-generates invoices on a schedule.
The scheduler job reads these and fires daily.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.recurring_invoice import RecurringInvoice
from app.models.user import User
from app.schemas.common import MessageResponse, Response

router = APIRouter(prefix="/api/recurring", tags=["recurring-invoices"])

VALID_FREQUENCIES = {"weekly", "monthly", "quarterly", "yearly"}


class RecurringItemIn(BaseModel):
    description: str
    quantity: float
    unit_price: float


class RecurringIn(BaseModel):
    client_id: uuid.UUID
    frequency: str
    items: list[RecurringItemIn]
    next_run_at: datetime


class RecurringOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    frequency: str
    items: list[dict]
    is_active: bool
    next_run_at: datetime
    last_run_at: datetime | None

    model_config = {"from_attributes": True}


def _to_out(r: RecurringInvoice) -> RecurringOut:
    return RecurringOut(
        id=r.id,
        client_id=r.client_id,
        client_name=r.client.name if r.client else "—",
        frequency=r.frequency,
        items=r.items,
        is_active=r.is_active,
        next_run_at=r.next_run_at,
        last_run_at=r.last_run_at,
    )


_load = (selectinload(RecurringInvoice.client),)


@router.get("", response_model=list[RecurringOut])
async def list_recurring(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.organization_id == current_user.organization_id)
        .options(*_load)
        .order_by(RecurringInvoice.next_run_at)
    )).scalars().all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=Response[RecurringOut], status_code=status.HTTP_201_CREATED)
async def create_recurring(
    payload: RecurringIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.frequency not in VALID_FREQUENCIES:
        raise HTTPException(status_code=400, detail=f"frequency must be one of {VALID_FREQUENCIES}")
    client = await db.get(Client, payload.client_id)
    if not client or client.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Client not found")

    rec = RecurringInvoice(
        organization_id=current_user.organization_id,
        client_id=payload.client_id,
        frequency=payload.frequency,
        items=[i.model_dump() for i in payload.items],
        next_run_at=payload.next_run_at,
    )
    db.add(rec)
    await db.flush()
    await db.refresh(rec)
    await db.refresh(rec, ["client"])
    return Response(data=_to_out(rec))


@router.patch("/{rec_id}/toggle", response_model=Response[RecurringOut])
async def toggle_recurring(
    rec_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = (await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec_id, RecurringInvoice.organization_id == current_user.organization_id)
        .options(*_load)
    )).scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recurring invoice not found")
    rec.is_active = not rec.is_active
    await db.flush()
    return Response(data=_to_out(rec))


@router.delete("/{rec_id}", response_model=MessageResponse)
async def delete_recurring(
    rec_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = await db.get(RecurringInvoice, rec_id)
    if not rec or rec.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Recurring invoice not found")
    await db.delete(rec)
    return MessageResponse(message="Recurring invoice deleted")
