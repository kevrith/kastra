import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role, ADMIN_ONLY
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.common import Meta, PaginatedResponse

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


class AuditLogOut:
    pass


from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    organization_id: str | None
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    detail: str | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=PaginatedResponse[AuditLogOut])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    user_id: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ONLY)),
):
    """List audit log entries for the organisation (admin only)."""
    q = select(AuditLog).where(AuditLog.organization_id == str(current_user.organization_id))

    if action:
        q = q.where(AuditLog.action == action)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    if from_date:
        q = q.where(AuditLog.created_at >= from_date)
    if to_date:
        q = q.where(AuditLog.created_at <= to_date)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    return PaginatedResponse(
        data=rows,
        meta=Meta(page=page, limit=limit, total=total, pages=math.ceil(total / limit) or 1),
    )


@router.get("/export/csv")
async def export_audit_csv(
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ONLY)),
):
    """Export audit log as CSV (admin only)."""
    import csv
    import io

    q = select(AuditLog).where(
        AuditLog.organization_id == str(current_user.organization_id)
    ).order_by(AuditLog.created_at.desc())

    if from_date:
        q = q.where(AuditLog.created_at >= from_date)
    if to_date:
        q = q.where(AuditLog.created_at <= to_date)

    rows = (await db.execute(q)).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Timestamp", "Action", "Resource Type", "Resource ID", "User ID", "Detail", "IP Address"])
    for r in rows:
        writer.writerow([
            r.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            r.action,
            r.resource_type,
            r.resource_id or "",
            r.user_id or "",
            r.detail or "",
            r.ip_address or "",
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=kastra-audit-log.csv"},
    )
