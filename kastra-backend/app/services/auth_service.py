import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.organization import Organization
from app.models.affiliate import Affiliate, AffiliateReferral
from app.models.user import User
from app.utils.plan_limits import VALID_PLANS
from app.utils.security import hash_password, verify_password


async def generate_org_prefix(db: AsyncSession, business_name: str) -> str:
    """Generate a unique prefix from business name."""
    words = business_name.upper().split()
    if len(words) >= 2:
        base_prefix = ''.join(word[0] for word in words[:3])
    else:
        base_prefix = business_name[:3].upper().replace(' ', '')
    
    prefix = base_prefix
    counter = 1
    while True:
        result = await db.execute(
            select(Organization).where(Organization.id_prefix == prefix)
        )
        if result.scalar_one_or_none() is None:
            break
        prefix = f"{base_prefix}{counter}"
        counter += 1
    
    return prefix


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user_with_org(
    db: AsyncSession,
    email: str,
    password: str,
    display_name: str,
    business_name: str,
    role: str = "admin",
    plan: str = "free",
    referral_code: str | None = None,
) -> User:
    now = datetime.now(timezone.utc)
    chosen_plan = plan if plan in VALID_PLANS else "free"
    is_trial = chosen_plan != "free"
    trial_ends_at = now + timedelta(days=14) if is_trial else None
    
    # Generate unique prefix from business name
    prefix = await generate_org_prefix(db, business_name)
    
    org = Organization(
        name=business_name,
        id_prefix=prefix,
        plan=chosen_plan,
        plan_status="active",
        billing_cycle_start=now,
        counters_reset_at=now,
        is_trial=is_trial,
        trial_ends_at=trial_ends_at,
    )
    db.add(org)
    await db.flush()

    user = User(
        organization_id=org.id,
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name,
        role=role,
    )
    db.add(user)
    await db.flush()

    if referral_code:
        aff = (await db.execute(
            select(Affiliate).where(Affiliate.code == referral_code.upper(), Affiliate.status == "active")
        )).scalar_one_or_none()
        if aff:
            db.add(AffiliateReferral(affiliate_id=aff.id, organization_id=org.id))
            await db.flush()

    await db.refresh(user, ["organization"])
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email).options(selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if user is None or user.hashed_password is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_google_user_info(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


async def get_or_create_google_user(db: AsyncSession, google_info: dict, plan: str = "free") -> User:
    google_id = google_info["id"]
    email = google_info["email"]
    display_name = google_info.get("name", email.split("@")[0])

    result = await db.execute(
        select(User).where(User.google_id == google_id).options(selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    result = await db.execute(
        select(User).where(User.email == email).options(selectinload(User.organization))
    )
    user = result.scalar_one_or_none()
    if user:
        user.google_id = google_id
        return user

    chosen_plan = plan if plan in VALID_PLANS else "free"
    now = datetime.now(timezone.utc)
    
    prefix = await generate_org_prefix(db, display_name)
    
    org = Organization(
        name=display_name,
        id_prefix=prefix,
        plan=chosen_plan,
        plan_status="active",
        billing_cycle_start=now,
        counters_reset_at=now,
        is_trial=chosen_plan != "free",
        trial_ends_at=now + timedelta(days=14) if chosen_plan != "free" else None,
    )
    db.add(org)
    await db.flush()

    user = User(
        organization_id=org.id,
        email=email,
        display_name=display_name,
        google_id=google_id,
        role="admin",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user, ["organization"])
    return user
