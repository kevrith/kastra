import math
import random
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.client import ClientCreate, ClientOut, ClientStats, ClientUpdate
from app.schemas.common import MessageResponse, Meta, PaginatedResponse, Response
from app.utils.security import hash_password

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=PaginatedResponse[ClientOut])
async def list_clients(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_clients")),
):
    q = select(Client).where(Client.organization_id == current_user.organization_id)
    if search:
        q = q.where(Client.name.ilike(f"%{search}%"))
    if status:
        q = q.where(Client.status == status)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(Client.name).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    clients = result.scalars().all()

    return PaginatedResponse(
        data=clients,
        meta=Meta(page=page, limit=limit, total=total, pages=math.ceil(total / limit)),
    )


@router.post("", response_model=Response[ClientOut], status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_create_clients")),
):
    client = Client(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return Response(data=client)


@router.get("/{client_id}", response_model=Response[ClientOut])
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_clients")),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.organization_id == current_user.organization_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return Response(data=client)


@router.put("/{client_id}", response_model=Response[ClientOut])
async def update_client(
    client_id: uuid.UUID,
    payload: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_edit_clients")),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.organization_id == current_user.organization_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    await db.flush()
    await db.refresh(client)
    return Response(data=client)


@router.delete("/{client_id}", response_model=MessageResponse)
async def delete_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_delete_clients")),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.organization_id == current_user.organization_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    await db.delete(client)
    return MessageResponse(message="Client deleted")


class PortalPinIn(BaseModel):
    pin: str  # 4-digit string


class PortalPinOut(BaseModel):
    pin_enabled: bool
    generated_pin: str | None = None  # returned only on generate


@router.post("/{client_id}/pin", response_model=PortalPinOut)
async def set_portal_pin(
    client_id: uuid.UUID,
    payload: PortalPinIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set or update the portal PIN for a client (business owner only)."""
    if len(payload.pin) != 4 or not payload.pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")
    client = (await db.execute(
        select(Client).where(Client.id == client_id, Client.organization_id == current_user.organization_id)
    )).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.portal_pin_hash = hash_password(payload.pin)
    await db.flush()
    return PortalPinOut(pin_enabled=True)


@router.post("/{client_id}/pin/generate", response_model=PortalPinOut)
async def generate_portal_pin(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-generate a random 4-digit PIN and return it (shown once)."""
    client = (await db.execute(
        select(Client).where(Client.id == client_id, Client.organization_id == current_user.organization_id)
    )).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    pin = f"{random.randint(0, 9999):04d}"
    client.portal_pin_hash = hash_password(pin)
    await db.flush()
    return PortalPinOut(pin_enabled=True, generated_pin=pin)


@router.delete("/{client_id}/pin", response_model=PortalPinOut)
async def remove_portal_pin(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove the portal PIN — portal becomes link-only again."""
    client = (await db.execute(
        select(Client).where(Client.id == client_id, Client.organization_id == current_user.organization_id)
    )).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.portal_pin_hash = None
    await db.flush()
    return PortalPinOut(pin_enabled=False)


@router.get("/{client_id}/history", response_model=Response[ClientStats])
async def client_history(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.organization_id == current_user.organization_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    stats_result = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.grand_total), 0).label("total_billed"),
            func.count(Invoice.id).label("invoice_count"),
            func.count(Invoice.id).filter(Invoice.payment_status == "paid").label("paid_count"),
            func.count(Invoice.id).filter(Invoice.payment_status == "unpaid").label("unpaid_count"),
        ).where(Invoice.client_id == client_id, Invoice.organization_id == current_user.organization_id)
    )
    row = stats_result.one()
    return Response(
        data=ClientStats(
            total_billed=row.total_billed,
            invoice_count=row.invoice_count,
            paid_count=row.paid_count,
            unpaid_count=row.unpaid_count,
        )
    )
