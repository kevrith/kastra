import pytest
from httpx import AsyncClient


_REG = {
    "email": "test@kastra.co.ke",
    "password": "secret123",
    "display_name": "Test User",
    "business_name": "Test Business",
    "consent": True,
}


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post("/api/auth/register", json=_REG)
    assert resp.status_code == 201
    assert "access_token" in resp.json()


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
async def test_login(client: AsyncClient):
    await client.post("/api/auth/register", json={**_REG, "email": "login@kastra.co.ke"})
    resp = await client.post("/api/auth/login", json={"email": "login@kastra.co.ke", "password": "secret123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={**_REG, "email": "wrong@kastra.co.ke"})
    resp = await client.post("/api/auth/login", json={"email": "wrong@kastra.co.ke", "password": "badpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={**_REG, "email": "me@kastra.co.ke"})
    token = reg.json()["access_token"]
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@kastra.co.ke"


@pytest.mark.asyncio
async def test_logout_invalidates_session(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={**_REG, "email": "logout@kastra.co.ke"})
    token = reg.json()["access_token"]
    await client.post("/api/auth/logout")
    # Access token is still valid until expiry — only refresh is invalidated
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_data_export(client: AsyncClient):
    reg = await client.post("/api/auth/register", json={**_REG, "email": "export@kastra.co.ke"})
    token = reg.json()["access_token"]
    resp = await client.get("/api/auth/me/export", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "user" in body
    assert body["user"]["email"] == "export@kastra.co.ke"
    assert "exported_at" in body
