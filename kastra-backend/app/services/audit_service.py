"""Lightweight audit logging for financial actions (Kenya DPA 2019 accountability)."""
import logging

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def client_ip(request: Request | None) -> str | None:
    """Caller IP, honouring the proxy header — the app runs behind Render's edge,
    so request.client.host alone is always the proxy, never the user."""
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


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


async def log_for_user(
    db: AsyncSession,
    user,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: str | None = None,
    request: Request | None = None,
) -> None:
    """Audit an action performed by a signed-in user.

    Thin wrapper over log_action that fills organization_id/user_id/ip from the
    caller, so business routers need one line instead of six.
    """
    await log_action(
        db,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        organization_id=str(user.organization_id) if user is not None else None,
        user_id=str(user.id) if user is not None else None,
        ip_address=client_ip(request),
    )


async def log_independent(
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
    """Audit an event in its own transaction.

    get_db() rolls the request session back on any exception, so events that end
    in an HTTP error — a failed login above all — would otherwise leave no trace.
    Those are exactly the events a security review asks for, so they get a
    session that commits independently of the request's outcome.

    The new session borrows the caller's engine rather than the module-level
    factory, so it always targets whatever database the request is actually
    using — including the one a test fixture has swapped in. (db.get_bind()
    returns the sync facade, which AsyncSession rejects; db.bind is the
    AsyncEngine itself.)
    """
    try:
        async with AsyncSession(bind=db.bind, expire_on_commit=False) as session:
            session.add(AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail,
                organization_id=str(organization_id) if organization_id else None,
                user_id=str(user_id) if user_id else None,
                ip_address=ip_address,
            ))
            await session.commit()
    except Exception:
        logger.exception("Failed to write independent audit log entry")
