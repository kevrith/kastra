import uuid

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.utils.security import decode_access_token, decode_refresh_token

bearer_scheme = HTTPBearer()

# ── Role default permissions ──────────────────────────────────────────────────
# admin gets everything. For other roles, this is the BASELINE.
# Per-user overrides in user_permissions table can EXPAND (never restrict) these.
ROLE_DEFAULTS: dict[str, set[str]] = {
    "admin": {
        "can_view_invoices", "can_create_invoices", "can_edit_invoices", "can_delete_invoices",
        "can_view_quotations", "can_create_quotations", "can_edit_quotations", "can_delete_quotations",
        "can_view_clients", "can_create_clients", "can_edit_clients", "can_delete_clients",
        "can_view_reports", "can_view_expenses", "can_create_expenses",
        "can_view_projects", "can_manage_projects",
    },
    "manager": {
        "can_view_invoices", "can_create_invoices", "can_edit_invoices",
        "can_view_quotations", "can_create_quotations", "can_edit_quotations",
        "can_view_clients", "can_create_clients", "can_edit_clients",
        "can_view_reports", "can_view_expenses", "can_create_expenses",
        "can_view_projects", "can_manage_projects",
    },
    "field_agent": {
        "can_view_projects", "can_manage_projects",
    },
    "viewer": {
        "can_view_invoices", "can_view_quotations", "can_view_clients",
        "can_view_reports", "can_view_projects",
    },
}


def _effective_permissions(user: User) -> set[str]:
    """Merge role defaults with any per-user overrides."""
    perms = set(ROLE_DEFAULTS.get(user.role, set()))
    if user.permissions:
        p = user.permissions
        for col in [
            "can_view_invoices", "can_create_invoices", "can_edit_invoices", "can_delete_invoices",
            "can_view_quotations", "can_create_quotations", "can_edit_quotations", "can_delete_quotations",
            "can_view_clients", "can_create_clients", "can_edit_clients", "can_delete_clients",
            "can_view_reports", "can_view_expenses", "can_create_expenses",
            "can_view_projects", "can_manage_projects",
        ]:
            if getattr(p, col, False):
                perms.add(col)
    return perms


def require_permission(permission: str):
    """FastAPI dependency — raises 403 if user lacks the permission."""
    async def _check(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = decode_access_token(credentials.credentials)
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
            .options(selectinload(User.permissions))
        )
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise credentials_exception

        if permission not in _effective_permissions(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {permission}",
            )
        return user
    return _check


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
        .options(selectinload(User.permissions))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def get_current_user_from_refresh(
    refresh_token: str = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
    try:
        payload = decode_refresh_token(refresh_token)
        user_id: str = payload.get("sub")
        token_ver: int = payload.get("ver", 0)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.token_version != token_ver:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please log in again.")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_manager_or_above(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin access required")
    return current_user
