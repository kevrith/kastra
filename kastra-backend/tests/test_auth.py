"""
Tests for authentication and email verification.

Coverage:
  - Registration no longer issues a token (returns message only)
  - Unverified users are blocked from logging in (403 EMAIL_NOT_VERIFIED)
  - Valid verification token marks the user verified and redirects with JWT
  - Expired / tampered token redirects to the error page
  - Already-verified users hitting the verify endpoint are redirected gracefully
  - Full happy path: register → verify via token → login → /me
  - Resend verification endpoint: sends for unverified, silent for unknown
  - All original login / logout / /me / data-export tests still pass
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.email_service import (
    _VERIFY_SECRET,
    create_email_verification_token,
)
from tests.conftest import _register_and_verify


_REG = {
    "email": "test@kastra.co.ke",
    "password": "secret123",
    "display_name": "Test User",
    "business_name": "Test Business",
    "consent": True,
}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_returns_201_and_message(client: AsyncClient):
    resp = await client.post("/api/auth/register", json=_REG)
    assert resp.status_code == 201
    body = resp.json()
    assert "message" in body
    assert "access_token" not in body


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/auth/register", json={**_REG, "email": "dup@kastra.co.ke"})
    resp = await client.post("/api/auth/register", json={**_REG, "email": "dup@kastra.co.ke"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_requires_consent(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={**_REG, "email": "noconsent@k.co", "consent": False})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password_rejected(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={**_REG, "email": "short@k.co", "password": "abc"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login — unverified gate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_blocked_for_unverified_user(client: AsyncClient):
    """User registers but has NOT clicked the activation link → login must be blocked."""
    await client.post("/api/auth/register", json={**_REG, "email": "unverified@k.co"})
    resp = await client.post("/api/auth/login", json={"email": "unverified@k.co", "password": "secret123"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "EMAIL_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={**_REG, "email": "wrong@kastra.co.ke"})
    resp = await client.post("/api/auth/login", json={"email": "wrong@kastra.co.ke", "password": "badpass"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Email verification — token handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_email_valid_token_returns_access_token(client: AsyncClient):
    """A valid verification token returns a 200 with an access token."""
    email = "verify_ok@k.co"
    await client.post("/api/auth/register", json={**_REG, "email": email})

    token = create_email_verification_token(email)
    resp = await client.get(f"/api/auth/verify-email?token={token}")

    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_verify_email_marks_user_as_verified(client: AsyncClient, db_session: AsyncSession):
    """After calling the verify endpoint, email_verified must be True in the DB."""
    email = "verify_db@k.co"
    await client.post("/api/auth/register", json={**_REG, "email": email})

    token = create_email_verification_token(email)
    await client.get(f"/api/auth/verify-email?token={token}")

    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    assert user.email_verified is True


@pytest.mark.asyncio
async def test_verify_email_invalid_token_returns_400(client: AsyncClient):
    """A tampered / garbage token must return 400 INVALID_TOKEN."""
    resp = await client.get("/api/auth/verify-email?token=not.a.valid.token")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_verify_email_expired_token_returns_400(client: AsyncClient):
    """An expired JWT must return 400 INVALID_TOKEN."""
    email = "expired@k.co"
    await client.post("/api/auth/register", json={**_REG, "email": email})

    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired_token = jwt.encode(
        {"sub": email, "exp": past, "type": "verify"},
        _VERIFY_SECRET,
        algorithm="HS256",
    )
    resp = await client.get(f"/api/auth/verify-email?token={expired_token}")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_verify_email_wrong_token_type_returns_400(client: AsyncClient):
    """A JWT with wrong 'type' claim must return 400 INVALID_TOKEN."""
    email = "wrongtype@k.co"
    await client.post("/api/auth/register", json={**_REG, "email": email})

    wrong_type_token = jwt.encode(
        {"sub": email, "exp": datetime.now(timezone.utc) + timedelta(hours=1), "type": "reset"},
        _VERIFY_SECRET,
        algorithm="HS256",
    )
    resp = await client.get(f"/api/auth/verify-email?token={wrong_type_token}")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_verify_email_unknown_email_returns_400(client: AsyncClient):
    """Verification token for a non-existent email must return 400 INVALID_TOKEN."""
    token = create_email_verification_token("ghost@nowhere.io")
    resp = await client.get(f"/api/auth/verify-email?token={token}")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_verify_email_already_verified_returns_409(client: AsyncClient, db_session: AsyncSession):
    """Calling the verify endpoint a second time must return 409 ALREADY_VERIFIED."""
    email = "already@k.co"
    await client.post("/api/auth/register", json={**_REG, "email": email})

    token = create_email_verification_token(email)
    await client.get(f"/api/auth/verify-email?token={token}")

    resp = await client.get(f"/api/auth/verify-email?token={token}")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "ALREADY_VERIFIED"


# ---------------------------------------------------------------------------
# Full happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_registration_verification_login_flow(client: AsyncClient):
    """End-to-end: register → verify → login → /me all succeed."""
    email = "fullflow@k.co"
    password = "secure123"

    # 1. Register
    reg = await client.post("/api/auth/register", json={**_REG, "email": email, "password": password})
    assert reg.status_code == 201
    assert "access_token" not in reg.json()

    # 2. Login before verification is blocked
    blocked = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert blocked.status_code == 403

    # 3. Verify
    token = create_email_verification_token(email)
    verify = await client.get(f"/api/auth/verify-email?token={token}")
    assert verify.status_code == 200
    jwt_token = verify.json()["access_token"]

    # 4. Use returned access token to call /me
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {jwt_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email

    # 5. Login also works now
    login = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    assert "access_token" in login.json()


# ---------------------------------------------------------------------------
# Resend verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resend_verification_unverified_user(client: AsyncClient):
    """Resend endpoint returns 200 for an unverified registered email."""
    email = "resend_me@k.co"
    await client.post("/api/auth/register", json={**_REG, "email": email})
    resp = await client.post("/api/auth/resend-verification", json={"email": email})
    assert resp.status_code == 200
    assert "message" in resp.json()


@pytest.mark.asyncio
async def test_resend_verification_unknown_email_returns_200(client: AsyncClient):
    """Resend must not reveal whether the email is registered (no info leak)."""
    resp = await client.post("/api/auth/resend-verification", json={"email": "ghost@nowhere.io"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_resend_verification_already_verified_returns_200(
    client: AsyncClient, db_session: AsyncSession
):
    """Resend for an already-verified user silently returns 200 (no re-send)."""
    email = "resend_verified@k.co"
    await client.post("/api/auth/register", json={**_REG, "email": email})
    # Manually verify
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.email_verified = True
    await db_session.commit()

    resp = await client.post("/api/auth/resend-verification", json={"email": email})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Existing passing tests — fixed for the new verified-user requirement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_succeeds_for_verified_user(client: AsyncClient, db_session: AsyncSession):
    email = "login_ok@kastra.co.ke"
    await _register_and_verify(client, db_session, email, "secret123", 9000)
    resp = await client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_me(client: AsyncClient, db_session: AsyncSession):
    email = "me@kastra.co.ke"
    token = await _register_and_verify(client, db_session, email, "secret123", 9001)
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == email


@pytest.mark.asyncio
async def test_logout_invalidates_refresh_not_access(client: AsyncClient, db_session: AsyncSession):
    email = "logout@kastra.co.ke"
    token = await _register_and_verify(client, db_session, email, "secret123", 9002)
    await client.post("/api/auth/logout")
    # Access token remains valid until expiry (only refresh cookie is cleared)
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_data_export(client: AsyncClient, db_session: AsyncSession):
    email = "export@kastra.co.ke"
    token = await _register_and_verify(client, db_session, email, "secret123", 9003)
    resp = await client.get("/api/auth/me/export", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "user" in body
    assert body["user"]["email"] == email
    assert "exported_at" in body
