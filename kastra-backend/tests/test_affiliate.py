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
    import random, string
    prefix = "".join(random.choices(string.ascii_uppercase, k=4))
    return Organization(
        id=uuid.uuid4(),
        name="Test Org",
        id_prefix=prefix,
        plan=plan,
        plan_status="active",
        is_trial=is_trial,
    )


# ---------------------------------------------------------------------------
# Referral code linking on registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_referral_code_linked_on_registration(client: AsyncClient, db_session: AsyncSession):
    aff = _make_affiliate(status="active", code="REFER1")
    db_session.add(aff)
    await db_session.commit()

    resp = await client.post("/api/auth/register", json={
        "business_name": "Referred Biz",
        "email": f"biz-{uuid.uuid4().hex[:6]}@test.com",
        "password": "password123",
        "display_name": "Owner",
        "consent": True,
        "plan": "free",
        "referral_code": "REFER1",
    })
    assert resp.status_code == 201

    from sqlalchemy import select
    row = (await db_session.execute(
        select(AffiliateReferral).where(AffiliateReferral.affiliate_id == aff.id)
    )).scalar_one_or_none()
    assert row is not None


@pytest.mark.asyncio
async def test_invalid_referral_code_is_ignored(client: AsyncClient, db_session: AsyncSession):
    resp = await client.post("/api/auth/register", json={
        "business_name": "No Ref Biz",
        "email": f"noref-{uuid.uuid4().hex[:6]}@test.com",
        "password": "password123",
        "display_name": "Owner",
        "consent": True,
        "plan": "free",
        "referral_code": "DOESNOTEXIST",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_suspended_affiliate_code_is_ignored(client: AsyncClient, db_session: AsyncSession):
    aff = _make_affiliate(status="suspended", code="SUSPEN1")
    db_session.add(aff)
    await db_session.commit()

    resp = await client.post("/api/auth/register", json={
        "business_name": "Suspended Ref Biz",
        "email": f"susref-{uuid.uuid4().hex[:6]}@test.com",
        "password": "password123",
        "display_name": "Owner",
        "consent": True,
        "plan": "free",
        "referral_code": "SUSPEN1",
    })
    assert resp.status_code == 201

    from sqlalchemy import select
    row = (await db_session.execute(
        select(AffiliateReferral).where(AffiliateReferral.affiliate_id == aff.id)
    )).scalar_one_or_none()
    assert row is None


# ---------------------------------------------------------------------------
# Affiliate registration & login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_affiliate_self_register(client: AsyncClient):
    resp = await client.post("/api/affiliate/register", json={
        "name": "Jane Partner",
        "email": f"jane-{uuid.uuid4().hex[:6]}@partner.com",
        "phone": "0700111222",
        "password": "password123",
        "payout_phone": "0700111222",
    })
    assert resp.status_code == 201
    assert "code" in resp.json()


@pytest.mark.asyncio
async def test_affiliate_register_duplicate_email(client: AsyncClient, db_session: AsyncSession):
    email = f"dup-{uuid.uuid4().hex[:6]}@partner.com"
    aff = _make_affiliate(code=f"DUP{uuid.uuid4().hex[:4].upper()}")
    aff.email = email
    db_session.add(aff)
    await db_session.commit()

    resp = await client.post("/api/affiliate/register", json={
        "name": "Another",
        "email": email,
        "phone": "0700000000",
        "password": "password123",
        "payout_phone": "0700000000",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_affiliate_login_pending(client: AsyncClient, db_session: AsyncSession):
    aff = _make_affiliate(status="pending", code=f"PEND{uuid.uuid4().hex[:4].upper()}")
    db_session.add(aff)
    await db_session.commit()

    resp = await client.post("/api/affiliate/login", json={"email": aff.email, "password": "password123"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_affiliate_login_active(client: AsyncClient, db_session: AsyncSession):
    aff = _make_affiliate(status="active", code=f"ACTV{uuid.uuid4().hex[:4].upper()}")
    db_session.add(aff)
    await db_session.commit()

    resp = await client.post("/api/affiliate/login", json={"email": aff.email, "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# ---------------------------------------------------------------------------
# Commission scheduler logic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_commission_credited_for_paying_org(db_session: AsyncSession):
    from app.services.scheduler import _credit_affiliate_commissions

    aff = _make_affiliate(status="active", code=f"COM{uuid.uuid4().hex[:4].upper()}")
    db_session.add(aff)

    paying_org = _make_org(plan="business", is_trial=False)
    free_org = _make_org(plan="free", is_trial=False)
    trial_org = _make_org(plan="starter", is_trial=True)
    db_session.add_all([paying_org, free_org, trial_org])
    await db_session.flush()

    db_session.add(AffiliateReferral(affiliate_id=aff.id, organization_id=paying_org.id))
    db_session.add(AffiliateReferral(affiliate_id=aff.id, organization_id=free_org.id))
    db_session.add(AffiliateReferral(affiliate_id=aff.id, organization_id=trial_org.id))
    await db_session.commit()

    with patch("app.services.scheduler.AsyncSessionLocal") as mock_session:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session.return_value = mock_cm

        await _credit_affiliate_commissions()

    from sqlalchemy import select
    commissions = (await db_session.execute(
        select(AffiliateCommission).where(AffiliateCommission.affiliate_id == aff.id)
    )).scalars().all()

    assert len(commissions) == 1
    assert commissions[0].organization_id == paying_org.id


@pytest.mark.asyncio
async def test_commission_not_double_credited(db_session: AsyncSession):
    from app.services.scheduler import _credit_affiliate_commissions

    aff = _make_affiliate(status="active", code=f"NODBL{uuid.uuid4().hex[:4].upper()}")
    db_session.add(aff)
    org = _make_org(plan="business", is_trial=False)
    db_session.add(org)
    await db_session.flush()

    db_session.add(AffiliateReferral(affiliate_id=aff.id, organization_id=org.id))
    await db_session.commit()

    with patch("app.services.scheduler.AsyncSessionLocal") as mock_session:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=db_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session.return_value = mock_cm

        await _credit_affiliate_commissions()
        await _credit_affiliate_commissions()

    from sqlalchemy import select, func
    count = (await db_session.execute(
        select(func.count(AffiliateCommission.id)).where(AffiliateCommission.affiliate_id == aff.id)
    )).scalar()
    assert count == 1


# ---------------------------------------------------------------------------
# Referral code check endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_valid_code(client: AsyncClient, db_session: AsyncSession):
    aff = _make_affiliate(status="active", code="VALID1")
    db_session.add(aff)
    await db_session.commit()

    resp = await client.get("/api/affiliate/check/VALID1")
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


@pytest.mark.asyncio
async def test_check_inactive_code_returns_404(client: AsyncClient, db_session: AsyncSession):
    aff = _make_affiliate(status="pending", code="PEND99")
    db_session.add(aff)
    await db_session.commit()

    resp = await client.get("/api/affiliate/check/PEND99")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Superadmin affiliate management
# ---------------------------------------------------------------------------

async def _sa_token(client: AsyncClient) -> str:
    from app.config import settings
    resp = await client.post("/api/superadmin/login", json={
        "username": settings.superadmin_username,
        "password": settings.superadmin_password,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_sa_list_affiliates(client: AsyncClient, db_session: AsyncSession):
    aff = _make_affiliate(code=f"SA{uuid.uuid4().hex[:4].upper()}")
    db_session.add(aff)
    await db_session.commit()

    token = await _sa_token(client)
    resp = await client.get(
        "/api/superadmin/affiliates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_sa_approve_affiliate(client: AsyncClient, db_session: AsyncSession):
    aff = _make_affiliate(status="pending", code=f"APP{uuid.uuid4().hex[:4].upper()}")
    db_session.add(aff)
    await db_session.commit()

    token = await _sa_token(client)
    resp = await client.patch(
        f"/api/superadmin/affiliates/{aff.id}/status",
        json={"status": "active"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    await db_session.refresh(aff)
    assert aff.status == "active"
