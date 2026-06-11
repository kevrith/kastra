import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User


def create_invite_token(email: str, organization_id: str) -> str:
    """Create a JWT invite token valid for 48 hours"""
    expires = datetime.now(timezone.utc) + timedelta(hours=48)
    payload = {
        "sub": email,
        "org_id": organization_id,
        "exp": expires,
        "type": "invite"
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_invite_token(token: str) -> dict:
    """Verify and decode invite token"""
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if payload.get("type") != "invite":
        raise ValueError("Invalid token type")
    return payload


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_invited_user(
    db: AsyncSession,
    email: str,
    display_name: str,
    role: str,
    organization_id: uuid.UUID,
    invited_by_id: uuid.UUID
) -> User:
    """Create a user record with invite token (no password yet)"""
    invite_token = create_invite_token(email, str(organization_id))
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    
    user = User(
        id=uuid.uuid4(),
        organization_id=organization_id,
        email=email,
        display_name=display_name,
        role=role,
        hashed_password=None,  # Set when they accept invite
        is_active=False,  # Activated when they accept
        email_verified=True,  # Invite link itself proves email ownership
        invite_token=invite_token,
        invite_token_expires_at=expires_at,
        invited_by=invited_by_id,
        invited_at=datetime.now(timezone.utc)
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
