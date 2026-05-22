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
    TeamMemberOut,
    UpdateTeamMemberRequest,
)
from app.services.email_service import _send as send_email
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
    result = await db.execute(
        select(User)
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.created_at.desc())
    )
    return result.scalars().all()


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
    
    # Send invite email
    from app.config import settings
    invite_link = f"{settings.frontend_url}/auth/accept-invite?token={user.invite_token}"
    
    await send_email(
        to_email=user.email,
        subject=f"You've been invited to join {current_user.organization.name} on Kastra",
        html_content=f"""
        <h2>You've been invited!</h2>
        <p>{current_user.display_name} has invited you to join <strong>{current_user.organization.name}</strong> on Kastra.</p>
        <p>Your role: <strong>{user.role}</strong></p>
        <p><a href="{invite_link}">Click here to accept the invitation and set your password</a></p>
        <p>This link expires in 48 hours.</p>
        """
    )
    
    return user


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
        if payload.role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"
            )
        user.role = payload.role
    
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
