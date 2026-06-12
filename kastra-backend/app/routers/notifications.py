import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str
    entity_id: str | None
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int


@router.get("", response_model=NotificationListOut)
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Notification)
        .where(Notification.organization_id == current_user.organization_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )).scalars().all()
    unread = sum(1 for n in rows if n.read_at is None)
    return NotificationListOut(items=rows, unread_count=unread)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = await db.get(Notification, notification_id)
    if not n or n.organization_id != current_user.organization_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found")
    if not n.read_at:
        n.read_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(n)
    return n


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Notification)
        .where(
            Notification.organization_id == current_user.organization_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    return MessageResponse(message="All notifications marked as read")
