"""Two-factor authentication: setup, enable, the login challenge, recovery codes."""
import pyotp
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def _email_of(client: AsyncClient, headers: dict) -> str:
    return (await client.get("/api/auth/me", headers=headers)).json()["email"]


async def _enable(client: AsyncClient, headers: dict) -> tuple[str, list[str]]:
    """Turn 2FA on and hand back (secret, backup codes)."""
    setup = (await client.post("/api/auth/2fa/setup", headers=headers)).json()
    secret = setup["secret"]
    resp = await client.post(
        "/api/auth/2fa/enable", json={"code": pyotp.TOTP(secret).now()}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    return secret, resp.json()["backup_codes"]


# ── Setup ────────────────────────────────────────────────────────────────────

async def test_setup_returns_a_scannable_secret(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/auth/2fa/setup", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["secret"]) == 32
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert body["qr_data_uri"].startswith("data:image/png;base64,")


async def test_setup_alone_does_not_enable_2fa(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """An abandoned setup must not lock the account."""
    await client.post("/api/auth/2fa/setup", headers=auth_headers)
    status = (await client.get("/api/auth/2fa/status", headers=auth_headers)).json()
    assert status["enabled"] is False


async def test_a_wrong_code_does_not_enable_2fa(client: AsyncClient, auth_headers: dict):
    await client.post("/api/auth/2fa/setup", headers=auth_headers)
    resp = await client.post("/api/auth/2fa/enable", json={"code": "000000"}, headers=auth_headers)
    assert resp.status_code == 400
    assert (await client.get("/api/auth/2fa/status", headers=auth_headers)).json()["enabled"] is False


async def test_enabling_returns_ten_backup_codes(client: AsyncClient, auth_headers: dict):
    _, codes = await _enable(client, auth_headers)
    assert len(codes) == 10
    assert len(set(codes)) == 10
    status = (await client.get("/api/auth/2fa/status", headers=auth_headers)).json()
    assert status["enabled"] is True
    assert status["backup_codes_remaining"] == 10


# ── The login challenge ──────────────────────────────────────────────────────

async def test_login_returns_a_challenge_not_a_session(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    email = await _email_of(client, auth_headers)
    secret, _ = await _enable(client, auth_headers)

    resp = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mfa_required"] is True
    assert body["access_token"] is None, "a password alone must not yield a session"
    assert body["mfa_token"]


async def test_a_valid_code_completes_the_login(client: AsyncClient, auth_headers: dict):
    email = await _email_of(client, auth_headers)
    secret, _ = await _enable(client, auth_headers)

    challenge = (await client.post(
        "/api/auth/login", json={"email": email, "password": "testpass123"}
    )).json()
    resp = await client.post("/api/auth/2fa/verify-login", json={
        "mfa_token": challenge["mfa_token"], "code": pyotp.TOTP(secret).now(),
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


async def test_a_wrong_code_is_rejected(client: AsyncClient, auth_headers: dict):
    email = await _email_of(client, auth_headers)
    await _enable(client, auth_headers)
    challenge = (await client.post(
        "/api/auth/login", json={"email": email, "password": "testpass123"}
    )).json()
    resp = await client.post("/api/auth/2fa/verify-login", json={
        "mfa_token": challenge["mfa_token"], "code": "111111",
    })
    assert resp.status_code == 401


async def test_the_challenge_token_is_not_a_session_token(client: AsyncClient, auth_headers: dict):
    """The half-finished login must not authenticate anything on its own."""
    email = await _email_of(client, auth_headers)
    await _enable(client, auth_headers)
    challenge = (await client.post(
        "/api/auth/login", json={"email": email, "password": "testpass123"}
    )).json()

    resp = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {challenge['mfa_token']}"}
    )
    assert resp.status_code in (401, 403)


# ── Recovery codes ───────────────────────────────────────────────────────────

async def test_a_backup_code_signs_you_in_once(client: AsyncClient, auth_headers: dict):
    email = await _email_of(client, auth_headers)
    _, codes = await _enable(client, auth_headers)

    challenge = (await client.post(
        "/api/auth/login", json={"email": email, "password": "testpass123"}
    )).json()
    first = await client.post("/api/auth/2fa/verify-login", json={
        "mfa_token": challenge["mfa_token"], "code": codes[0],
    })
    assert first.status_code == 200
    headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
    assert (await client.get("/api/auth/2fa/status", headers=headers)).json()["backup_codes_remaining"] == 9

    # the same code must not work again
    challenge2 = (await client.post(
        "/api/auth/login", json={"email": email, "password": "testpass123"}
    )).json()
    replay = await client.post("/api/auth/2fa/verify-login", json={
        "mfa_token": challenge2["mfa_token"], "code": codes[0],
    })
    assert replay.status_code == 401


# ── Disabling ────────────────────────────────────────────────────────────────

async def test_disabling_requires_the_password(client: AsyncClient, auth_headers: dict):
    await _enable(client, auth_headers)
    bad = await client.post("/api/auth/2fa/disable", json={"password": "wrong"}, headers=auth_headers)
    assert bad.status_code == 400
    assert (await client.get("/api/auth/2fa/status", headers=auth_headers)).json()["enabled"] is True


async def test_disabling_clears_the_secret(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    email = await _email_of(client, auth_headers)
    await _enable(client, auth_headers)
    resp = await client.post(
        "/api/auth/2fa/disable", json={"password": "testpass123"}, headers=auth_headers
    )
    assert resp.status_code == 200

    # No expire_all(): the app and this test share one session in the fixture,
    # and the router's changes are pending rather than committed — expiring
    # would throw them away and re-read the pre-disable row.
    user = (await db_session.execute(select(User).where(User.email == email))).scalar_one()
    assert user.totp_enabled is False
    assert user.totp_secret is None
    assert user.totp_backup_codes is None
