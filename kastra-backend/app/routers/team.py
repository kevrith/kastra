from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.team import (
    AcceptInviteRequest,
    InviteUserRequest,
    PermissionsOut,
    TeamMemberOut,
    UpdatePermissionsRequest,
    UpdateTeamMemberRequest,
)
from app.models.user_permission import UserPermission
from app.services.team_service import (
    create_invited_user,
    get_user_by_email,
    verify_invite_token,
)
from app.utils.security import hash_password

router = APIRouter(prefix="/api/team", tags=["team"])

VALID_ROLES = ["admin", "manager", "field_agent", "viewer"]


@router.get("", response_model=list[TeamMemberOut])
async def list_team_members(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all team members in the organization (admin only)"""
    from app.config import settings
    result = await db.execute(
        select(User)
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.created_at.desc())
    )
    members = result.scalars().all()
    out = []
    for m in members:
        item = TeamMemberOut.model_validate(m)
        if m.invite_token:
            item.invite_link = f"{settings.frontend_url}/auth/accept-invite?token={m.invite_token}"
        out.append(item)
    return out


@router.post("/invite", response_model=TeamMemberOut, status_code=status.HTTP_201_CREATED)
async def invite_user(
    payload: InviteUserRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Invite a new team member (admin only)"""
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
        )
    
    # Check if user already exists
    existing = await get_user_by_email(db, payload.email)
    if existing:
        if existing.organization_id == current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists in your organization"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already registered with another organization"
            )
    
    # Create invited user
    user = await create_invited_user(
        db,
        email=payload.email,
        display_name=payload.display_name,
        role=payload.role,
        organization_id=current_user.organization_id,
        invited_by_id=current_user.id
    )

    from app.config import settings
    invite_link = f"{settings.frontend_url}/auth/accept-invite?token={user.invite_token}"

    # Return the invite link directly — admin shares it via WhatsApp/SMS
    result = TeamMemberOut.model_validate(user)
    result.invite_link = invite_link
    return result


@router.post("/accept-invite")
async def accept_invite(
    payload: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Accept an invite and set password"""
    try:
        token_data = verify_invite_token(payload.token)
        email = token_data.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite token"
        )
    
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.invite_token != payload.token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    
    if user.invite_token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite has expired")
    
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters"
        )
    
    # Activate user
    user.hashed_password = hash_password(payload.password)
    user.is_active = True
    user.invite_token = None
    user.invite_token_expires_at = None
    await db.commit()
    
    return {"message": "Invite accepted. You can now log in."}


@router.patch("/{user_id}", response_model=TeamMemberOut)
async def update_team_member(
    user_id: str,
    payload: UpdateTeamMemberRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update team member role or active status (admin only)"""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot modify your own role or status"
        )
    
    if payload.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role changes must be requested through the platform administrator"
        )

    if payload.is_active is not None:
        user.is_active = payload.is_active
        if not payload.is_active:
            # Invalidate all sessions when deactivating
            user.token_version += 1
    
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}")
async def remove_team_member(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Remove a team member (admin only)"""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself"
        )
    
    await db.delete(user)
    await db.commit()
    return {"message": "Team member removed"}


@router.post("/{user_id}/reset-password")
async def reset_team_member_password(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Send password reset email to a team member (admin only)"""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user uses Google login and cannot reset password"
        )
    
    # Use the existing password reset service
    from app.services.email_service import create_password_reset_token, send_password_reset_email
    token = create_password_reset_token(user.email)
    await send_password_reset_email(user.email, token)
    
    return {"message": "Password reset link sent"}


@router.get("/{user_id}/permissions", response_model=PermissionsOut)
async def get_member_permissions(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get effective permission overrides for a team member (admin only)"""
    from app.dependencies import ROLE_DEFAULTS
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    perm_result = await db.execute(
        select(UserPermission).where(UserPermission.user_id == user.id)
    )
    perm = perm_result.scalar_one_or_none()
    if not perm:
        return PermissionsOut()
    return PermissionsOut.model_validate(perm)


@router.put("/{user_id}/permissions", response_model=PermissionsOut)
async def set_member_permissions(
    user_id: str,
    payload: UpdatePermissionsRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Set permission overrides for a team member (admin only). Admins cannot have overrides."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Admins already have full access")

    perm_result = await db.execute(
        select(UserPermission).where(UserPermission.user_id == user.id)
    )
    perm = perm_result.scalar_one_or_none()

    if not perm:
        import uuid as _uuid
        perm = UserPermission(id=_uuid.uuid4(), user_id=user.id)
        db.add(perm)

    for field, value in payload.model_dump().items():
        setattr(perm, field, value)

    await db.commit()
    await db.refresh(perm)
    return PermissionsOut.model_validate(perm)
