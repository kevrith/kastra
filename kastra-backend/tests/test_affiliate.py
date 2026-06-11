"""Tests for the affiliate system."""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.affiliate import Affiliate, AffiliateCommission, AffiliateReferral
from app.models.organization import Organization
from app.utils.security import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_affiliate(status="active", balance=Decimal("0"), code="TESTCODE"):
    return Affiliate(
        id=uuid.uuid4(),
        name="Test Partner",
        email=f"partner-{uuid.uuid4().hex[:6]}@test.com",
        phone="0712000000",
        password_hash=hash_password("password123"),
        code=code,
        status=status,
        payout_phone="0712000000",
        balance_ksh=balance,
        total_earned_ksh=balance,
        total_paid_ksh=Decimal("0"),
    )


def _make_org(plan="business", is_trial=False):
    return Organization(
        id=uuid.uuid4(),
        name="Test Org",
        id_prefix="TO",
        plan=plan,
        plan_status="active",
        is_trial=is_trial,
    )


# ---------------------------------------------------------------------------
# Unit: referral code linking
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_referral_code_linked_on_registration(async_client: AsyncClient, db: AsyncSession):
    """Registering with a valid referral code creates an AffiliateReferral row."""
    aff = _make_affiliate(status="active", code="REFER1")
    db.add(aff)
    await db.commit()

    resp = await async_client.post("/api/auth/register", json={
        "business_name": "Referred Biz",
        "email": f"biz-{uuid.uuid4().hex[:6]}@test.com",
        "password": "password123",
        "display_name": "Owner",
        "consent": True,
        "plan": "free",
        "referral_code": "REFER1",
    })
    assert resp.status_code == 200

    from sqlalchemy import select
    row = (await db.execute(
        select(AffiliateReferral).where(AffiliateReferral.affiliate_id == aff.id)
    )).scalar_one_or_none()
    assert row is not None


@pytest.mark.asyncio
async def test_invalid_referral_code_is_ignored(async_client: AsyncClient, db: AsyncSession):
    """Registration with a non-existent referral code succeeds without error."""
    resp = await async_client.post("/api/auth/register", json={
        "business_name": "No Ref Biz",
        "email": f"noref-{uuid.uuid4().hex[:6]}@test.com",
        "password": "password123",
        "display_name": "Owner",
        "consent": True,
        "plan": "free",
        "referral_code": "DOESNOTEXIST",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_suspended_affiliate_code_is_ignored(async_client: AsyncClient, db: AsyncSession):
    """Suspended affiliate codes are not linked."""
    aff = _make_affiliate(status="suspended", code="SUSPEN1")
    db.add(aff)
    await db.commit()

    resp = await async_client.post("/api/auth/register", json={
        "business_name": "Suspended Ref Biz",
        "email": f"susref-{uuid.uuid4().hex[:6]}@test.com",
        "password": "password123",
        "display_name": "Owner",
        "consent": True,
        "plan": "free",
        "referral_code": "SUSPEN1",
    })
    assert resp.status_code == 200

    from sqlalchemy import select
    row = (await db.execute(
        select(AffiliateReferral).where(AffiliateReferral.affiliate_id == aff.id)
    )).scalar_one_or_none()
    assert row is None


# ---------------------------------------------------------------------------
# Unit: affiliate registration & login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_affiliate_self_register(async_client: AsyncClient):
    resp = await async_client.post("/api/affiliate/register", json={
        "name": "Jane Partner",
        "email": f"jane-{uuid.uuid4().hex[:6]}@partner.com",
        "phone": "0700111222",
        "password": "password123",
        "payout_phone": "0700111222",
    })
    assert resp.status_code == 201
    assert "code" in resp.json()


@pytest.mark.asyncio
async def test_affiliate_register_duplicate_email(async_client: AsyncClient, db: AsyncSession):
    email = f"dup-{uuid.uuid4().hex[:6]}@partner.com"
    aff = _make_affiliate(code=f"DUP{uuid.uuid4().hex[:4].upper()}")
    aff.email = email
    db.add(aff)
    await db.commit()

    resp = await async_client.post("/api/affiliate/register", json={
        "name": "Another",
        "email": email,
        "phone": "0700000000",
        "password": "password123",
        "payout_phone": "0700000000",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_affiliate_login_pending(async_client: AsyncClient, db: AsyncSession):
    aff = _make_affiliate(status="pending", code=f"PEND{uuid.uuid4().hex[:4].upper()}")
    db.add(aff)
    await db.commit()

    resp = await async_client.post("/api/affiliate/login", json={"email": aff.email, "password": "password123"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_affiliate_login_active(async_client: AsyncClient, db: AsyncSession):
    aff = _make_affiliate(status="active", code=f"ACTV{uuid.uuid4().hex[:4].upper()}")
    db.add(aff)
    await db.commit()

    resp = await async_client.post("/api/affiliate/login", json={"email": aff.email, "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# ---------------------------------------------------------------------------
# Unit: commission scheduler logic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_commission_credited_for_paying_org(db: AsyncSession):
    """Paying org generates commission; free/trial do not."""
    from app.services.scheduler import _credit_affiliate_commissions
    from datetime import datetime, timezone

    aff = _make_affiliate(status="active", code=f"COM{uuid.uuid4().hex[:4].upper()}")
    db.add(aff)

    paying_org = _make_org(plan="business", is_trial=False)
    free_org = _make_org(plan="free", is_trial=False)
    trial_org = _make_org(plan="starter", is_trial=True)
    db.add_all([paying_org, free_org, trial_org])
    await db.flush()

    db.add(AffiliateReferral(affiliate_id=aff.id, organization_id=paying_org.id))
    db.add(AffiliateReferral(affiliate_id=aff.id, organization_id=free_org.id))
    db.add(AffiliateReferral(affiliate_id=aff.id, organization_id=trial_org.id))
    await db.commit()

    # Patch AsyncSessionLocal to return our test db session
    with patch("app.services.scheduler.AsyncSessionLocal") as mock_session:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session.return_value = mock_cm

        await _credit_affiliate_commissions()

    from sqlalchemy import select
    commissions = (await db.execute(
        select(AffiliateCommission).where(AffiliateCommission.affiliate_id == aff.id)
    )).scalars().all()

    # Only one commission — for the paying org
    assert len(commissions) == 1
    assert commissions[0].organization_id == paying_org.id


@pytest.mark.asyncio
async def test_commission_not_double_credited(db: AsyncSession):
    """Same org is not credited twice for the same month."""
    from app.services.scheduler import _credit_affiliate_commissions
    from datetime import datetime, timezone

    aff = _make_affiliate(status="active", code=f"NODBL{uuid.uuid4().hex[:4].upper()}")
    db.add(aff)
    org = _make_org(plan="business", is_trial=False)
    db.add(org)
    await db.flush()

    db.add(AffiliateReferral(affiliate_id=aff.id, organization_id=org.id))
    await db.commit()

    with patch("app.services.scheduler.AsyncSessionLocal") as mock_session:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session.return_value = mock_cm

        await _credit_affiliate_commissions()
        await _credit_affiliate_commissions()  # run twice

    from sqlalchemy import select, func
    count = (await db.execute(
        select(func.count(AffiliateCommission.id)).where(AffiliateCommission.affiliate_id == aff.id)
    )).scalar()
    assert count == 1


# ---------------------------------------------------------------------------
# Unit: referral code check endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_valid_code(async_client: AsyncClient, db: AsyncSession):
    aff = _make_affiliate(status="active", code="VALID1")
    db.add(aff)
    await db.commit()

    resp = await async_client.get("/api/affiliate/check/VALID1")
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


@pytest.mark.asyncio
async def test_check_inactive_code_returns_404(async_client: AsyncClient, db: AsyncSession):
    aff = _make_affiliate(status="pending", code="PEND99")
    db.add(aff)
    await db.commit()

    resp = await async_client.get("/api/affiliate/check/PEND99")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Unit: superadmin affiliate management
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sa_list_affiliates(async_client: AsyncClient, db: AsyncSession):
    """Superadmin can list all affiliates."""
    from app.config import settings
    aff = _make_affiliate(code=f"SA{uuid.uuid4().hex[:4].upper()}")
    db.add(aff)
    await db.commit()

    resp = await async_client.get(
        "/api/superadmin/affiliates",
        headers={"Authorization": f"Bearer {settings.superadmin_secret_key}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_sa_approve_affiliate(async_client: AsyncClient, db: AsyncSession):
    from app.config import settings
    aff = _make_affiliate(status="pending", code=f"APP{uuid.uuid4().hex[:4].upper()}")
    db.add(aff)
    await db.commit()

    resp = await async_client.patch(
        f"/api/superadmin/affiliates/{aff.id}/status",
        json={"status": "active"},
        headers={"Authorization": f"Bearer {settings.superadmin_secret_key}"},
    )
    assert resp.status_code == 200

    await db.refresh(aff)
    assert aff.status == "active"
