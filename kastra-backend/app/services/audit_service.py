"""Lightweight audit logging for financial actions (Kenya DPA 2019 accountability)."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def log_action(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: str | None = None,
    organization_id: str | None = None,
    user_id: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Append an immutable audit record. Never raises — logs errors instead."""
    try:
        entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            organization_id=str(organization_id) if organization_id else None,
            user_id=str(user_id) if user_id else None,
            ip_address=ip_address,
        )
        db.add(entry)
    except Exception:
        logger.exception("Failed to write audit log entry")
