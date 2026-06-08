"""
Tests for the testimonials system:
  - Public GET /api/testimonials (landing page feed)
  - Superadmin CRUD via /api/superadmin/testimonials
"""
import pytest
from httpx import AsyncClient

from app.config import settings


# ---------------------------------------------------------------------------
# Helper: get a superadmin token
# ---------------------------------------------------------------------------

async def _sa_token(client: AsyncClient) -> str:
    resp = await client.post("/api/superadmin/login", json={
        "username": settings.superadmin_username,
        "password": settings.superadmin_password,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _sa_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Public endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_public_testimonials_returns_list(client: AsyncClient):
    """GET /api/testimonials is public and always returns a list."""
    resp = await client.get("/api/testimonials")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_public_testimonials_only_active(client: AsyncClient):
    """Hidden testimonials must not appear in the public feed."""
    token = await _sa_token(client)
    headers = _sa_headers(token)

    # Create one visible and one hidden testimonial
    await client.post("/api/superadmin/testimonials", json={
        "name": "Visible User", "role": "CEO", "text": "Great product!",
        "stars": 5, "is_active": True, "sort_order": 0,
    }, headers=headers)
    await client.post("/api/superadmin/testimonials", json={
        "name": "Hidden User", "role": "CFO", "text": "Not shown",
        "stars": 4, "is_active": False, "sort_order": 1,
    }, headers=headers)

    resp = await client.get("/api/testimonials")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "Visible User" in names
    assert "Hidden User" not in names


@pytest.mark.asyncio
async def test_public_testimonials_ordering(client: AsyncClient):
    """Public feed is ordered by sort_order ascending."""
    token = await _sa_token(client)
    headers = _sa_headers(token)

    await client.post("/api/superadmin/testimonials", json={
        "name": "Last", "role": "R", "text": "T", "stars": 5, "is_active": True, "sort_order": 10,
    }, headers=headers)
    await client.post("/api/superadmin/testimonials", json={
        "name": "First", "role": "R", "text": "T", "stars": 5, "is_active": True, "sort_order": 0,
    }, headers=headers)

    resp = await client.get("/api/testimonials")
    assert resp.status_code == 200
    data = resp.json()
    active = [t for t in data if t["name"] in ("First", "Last")]
    assert active[0]["name"] == "First"
    assert active[-1]["name"] == "Last"


# ---------------------------------------------------------------------------
# Superadmin — create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sa_create_testimonial(client: AsyncClient):
    token = await _sa_token(client)
    resp = await client.post("/api/superadmin/testimonials", json={
        "name": "Jane Doe", "role": "Founder, JD Ltd",
        "text": "Really transformed our billing workflow.",
        "stars": 5, "is_active": True, "sort_order": 0,
    }, headers=_sa_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Jane Doe"
    assert data["role"] == "Founder, JD Ltd"
    assert data["stars"] == 5
    assert "id" in data


@pytest.mark.asyncio
async def test_sa_create_clamps_stars(client: AsyncClient):
    """Stars outside 1–5 must be clamped, not fail."""
    token = await _sa_token(client)
    resp = await client.post("/api/superadmin/testimonials", json={
        "name": "Star Test", "role": "R", "text": "T", "stars": 99, "is_active": True, "sort_order": 0,
    }, headers=_sa_headers(token))
    assert resp.status_code == 200
    assert resp.json()["stars"] == 5


@pytest.mark.asyncio
async def test_sa_create_requires_auth(client: AsyncClient):
    resp = await client.post("/api/superadmin/testimonials", json={
        "name": "X", "role": "Y", "text": "Z", "stars": 5, "is_active": True, "sort_order": 0,
    })
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Superadmin — list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sa_list_includes_hidden(client: AsyncClient):
    """Superadmin list includes both active and hidden testimonials."""
    token = await _sa_token(client)
    headers = _sa_headers(token)

    await client.post("/api/superadmin/testimonials", json={
        "name": "SA Visible", "role": "R", "text": "T", "stars": 5, "is_active": True, "sort_order": 0,
    }, headers=headers)
    await client.post("/api/superadmin/testimonials", json={
        "name": "SA Hidden", "role": "R", "text": "T", "stars": 5, "is_active": False, "sort_order": 1,
    }, headers=headers)

    resp = await client.get("/api/superadmin/testimonials", headers=headers)
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "SA Visible" in names
    assert "SA Hidden" in names


# ---------------------------------------------------------------------------
# Superadmin — update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sa_update_testimonial(client: AsyncClient):
    token = await _sa_token(client)
    headers = _sa_headers(token)

    create_resp = await client.post("/api/superadmin/testimonials", json={
        "name": "Old Name", "role": "Old Role", "text": "Old text",
        "stars": 4, "is_active": True, "sort_order": 0,
    }, headers=headers)
    tid = create_resp.json()["id"]

    resp = await client.put(f"/api/superadmin/testimonials/{tid}", json={
        "name": "New Name", "role": "New Role", "text": "New text",
        "stars": 5, "is_active": True, "sort_order": 1,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["stars"] == 5


@pytest.mark.asyncio
async def test_sa_update_toggle_active(client: AsyncClient):
    """Toggling is_active via PUT should hide the testimonial from public feed."""
    token = await _sa_token(client)
    headers = _sa_headers(token)

    create_resp = await client.post("/api/superadmin/testimonials", json={
        "name": "Toggle Me", "role": "R", "text": "T", "stars": 5, "is_active": True, "sort_order": 0,
    }, headers=headers)
    tid = create_resp.json()["id"]

    # Deactivate
    await client.put(f"/api/superadmin/testimonials/{tid}", json={
        "name": "Toggle Me", "role": "R", "text": "T", "stars": 5, "is_active": False, "sort_order": 0,
    }, headers=headers)

    # Public feed must not include it
    pub_resp = await client.get("/api/testimonials")
    names = [t["name"] for t in pub_resp.json()]
    assert "Toggle Me" not in names


@pytest.mark.asyncio
async def test_sa_update_not_found(client: AsyncClient):
    token = await _sa_token(client)
    resp = await client.put(
        "/api/superadmin/testimonials/00000000-0000-0000-0000-000000000000",
        json={"name": "X", "role": "Y", "text": "Z", "stars": 5, "is_active": True, "sort_order": 0},
        headers=_sa_headers(token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Superadmin — delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sa_delete_testimonial(client: AsyncClient):
    token = await _sa_token(client)
    headers = _sa_headers(token)

    create_resp = await client.post("/api/superadmin/testimonials", json={
        "name": "Delete Me", "role": "R", "text": "T", "stars": 5, "is_active": True, "sort_order": 0,
    }, headers=headers)
    tid = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/superadmin/testimonials/{tid}", headers=headers)
    assert del_resp.status_code == 200

    # Should no longer appear in superadmin list
    list_resp = await client.get("/api/superadmin/testimonials", headers=headers)
    ids = [t["id"] for t in list_resp.json()]
    assert tid not in ids


@pytest.mark.asyncio
async def test_sa_delete_not_found(client: AsyncClient):
    token = await _sa_token(client)
    resp = await client.delete(
        "/api/superadmin/testimonials/00000000-0000-0000-0000-000000000000",
        headers=_sa_headers(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sa_delete_requires_auth(client: AsyncClient):
    resp = await client.delete("/api/superadmin/testimonials/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 403
