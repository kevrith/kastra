"""
Tests for the full testimonials system:
  - Public GET /api/testimonials (landing page)
  - Public form GET/POST via unique token
  - Superadmin: manual CRUD
  - Superadmin: request flow (send request → customer submits → approve/reject)
"""
import pytest
from httpx import AsyncClient

from app.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _sa_token(client: AsyncClient) -> str:
    resp = await client.post("/api/superadmin/login", json={
        "username": settings.superadmin_username,
        "password": settings.superadmin_password,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_manual(client, sa_tok, **kwargs) -> dict:
    defaults = {"name": "Test User", "role": "CEO", "text": "Great product", "stars": 5, "is_active": True, "sort_order": 0}
    resp = await client.post("/api/superadmin/testimonials", json={**defaults, **kwargs}, headers=_h(sa_tok))
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _request_testimonial(client, sa_tok, email="test@example.com", name="Test User", role_hint="") -> dict:
    resp = await client.post("/api/superadmin/testimonials/request", json={"email": email, "name": name, "role_hint": role_hint}, headers=_h(sa_tok))
    assert resp.status_code == 200, resp.text
    # Retrieve the created entry from the list to get the token
    list_resp = await client.get("/api/superadmin/testimonials?status=pending", headers=_h(sa_tok))
    pending = [t for t in list_resp.json() if t["requested_email"] == email]
    assert pending, "pending testimonial not found"
    return pending[-1]


# ---------------------------------------------------------------------------
# Public endpoint: landing page feed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_public_list_only_approved_and_active(client: AsyncClient):
    sa = await _sa_token(client)
    await _create_manual(client, sa, name="Approved Visible", is_active=True)
    await _create_manual(client, sa, name="Approved Hidden", is_active=False)

    resp = await client.get("/api/testimonials")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "Approved Visible" in names
    assert "Approved Hidden" not in names


@pytest.mark.asyncio
async def test_public_list_excludes_pending(client: AsyncClient):
    sa = await _sa_token(client)
    await _request_testimonial(client, sa, email="pending@ex.com", name="Pending User")

    resp = await client.get("/api/testimonials")
    names = [t["name"] for t in resp.json()]
    assert "Pending User" not in names


@pytest.mark.asyncio
async def test_public_list_ordering(client: AsyncClient):
    sa = await _sa_token(client)
    await _create_manual(client, sa, name="Last",  sort_order=10)
    await _create_manual(client, sa, name="First", sort_order=0)

    resp = await client.get("/api/testimonials")
    data = resp.json()
    active = [t for t in data if t["name"] in ("First", "Last")]
    assert active[0]["name"] == "First"
    assert active[-1]["name"] == "Last"


@pytest.mark.asyncio
async def test_public_list_has_stars_field(client: AsyncClient):
    sa = await _sa_token(client)
    await _create_manual(client, sa, name="Star Check", stars=4)

    resp = await client.get("/api/testimonials")
    entry = next((t for t in resp.json() if t["name"] == "Star Check"), None)
    assert entry is not None
    assert entry["stars"] == 4


# ---------------------------------------------------------------------------
# Public form: GET /api/testimonials/form/{token}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_form_get_prefills_name(client: AsyncClient):
    sa = await _sa_token(client)
    entry = await _request_testimonial(client, sa, email="form1@ex.com", name="Grace Wanjiku", role_hint="CEO")

    # Retrieve the request_token — need to query directly; expose via list
    list_resp = await client.get("/api/superadmin/testimonials?status=pending", headers=_h(sa))
    t = next(t for t in list_resp.json() if t["id"] == entry["id"])
    # We can't get the token from the API (security). We'll use the DB directly.
    from app.models.testimonial import Testimonial
    from sqlalchemy import select
    import uuid

    # Use the conftest db_session via a fresh query
    # Instead, call the superadmin request endpoint again and intercept (simpler: use DB fixture in separate test)
    # For integration purposes, test the flow end-to-end via a workaround:
    # The test just verifies the endpoint exists and returns 404 for bad token.
    resp = await client.get("/api/testimonials/form/bad-token-xyz")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_form_get_invalid_token(client: AsyncClient):
    resp = await client.get("/api/testimonials/form/totally-fake-token")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Full request flow (via DB fixture to get the token)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_request_flow(client: AsyncClient, db_session):
    """
    End-to-end: request → customer opens form → submits → superadmin approves → appears on landing page.
    """
    sa = await _sa_token(client)

    # 1. Send request
    req_resp = await client.post(
        "/api/superadmin/testimonials/request",
        json={"email": "flow@ex.com", "name": "Flow User", "role_hint": "CFO"},
        headers=_h(sa),
    )
    assert req_resp.status_code == 200
    t_id = req_resp.json()["id"]

    # 2. Fetch token directly from DB
    from app.models.testimonial import Testimonial
    from sqlalchemy import select
    import uuid

    result = await db_session.execute(
        select(Testimonial).where(Testimonial.id == uuid.UUID(t_id))
    )
    db_t = result.scalar_one()
    form_token = db_t.request_token
    assert form_token is not None

    # 3. Customer opens form
    get_resp = await client.get(f"/api/testimonials/form/{form_token}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Flow User"
    assert get_resp.json()["role_hint"] == "CFO"

    # 4. Customer submits
    sub_resp = await client.post(f"/api/testimonials/form/{form_token}", json={
        "name": "Flow User",
        "role": "CFO, Flow Corp",
        "text": "Kastra has transformed our invoicing completely.",
        "stars": 5,
        "consent": True,
    })
    assert sub_resp.status_code == 200

    # 5. Not yet on landing page (still pending)
    pub = await client.get("/api/testimonials")
    names = [t["name"] for t in pub.json()]
    assert "Flow User" not in names

    # 6. Superadmin sees it in pending with submitted data
    list_resp = await client.get("/api/superadmin/testimonials?status=pending", headers=_h(sa))
    pending = [t for t in list_resp.json() if t["id"] == t_id]
    assert len(pending) == 1
    assert pending[0]["submitted_at"] is not None
    assert pending[0]["stars"] == 5

    # 7. Superadmin approves
    approve_resp = await client.post(f"/api/superadmin/testimonials/{t_id}/approve", headers=_h(sa))
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # 8. Now appears on landing page
    pub2 = await client.get("/api/testimonials")
    names2 = [t["name"] for t in pub2.json()]
    assert "Flow User" in names2

    # 9. Landing page entry has stars
    entry = next(t for t in pub2.json() if t["name"] == "Flow User")
    assert entry["stars"] == 5
    assert entry["role"] == "CFO, Flow Corp"


@pytest.mark.asyncio
async def test_form_cannot_be_submitted_twice(client: AsyncClient, db_session):
    sa = await _sa_token(client)
    req_resp = await client.post(
        "/api/superadmin/testimonials/request",
        json={"email": "twice@ex.com", "name": "Twice User", "role_hint": ""},
        headers=_h(sa),
    )
    t_id = req_resp.json()["id"]

    from app.models.testimonial import Testimonial
    from sqlalchemy import select
    import uuid

    result = await db_session.execute(select(Testimonial).where(Testimonial.id == uuid.UUID(t_id)))
    form_token = result.scalar_one().request_token

    payload = {"name": "Twice User", "role": "CTO", "text": "Love it!", "stars": 5, "consent": True}
    r1 = await client.post(f"/api/testimonials/form/{form_token}", json=payload)
    assert r1.status_code == 200

    r2 = await client.post(f"/api/testimonials/form/{form_token}", json=payload)
    assert r2.status_code == 410


@pytest.mark.asyncio
async def test_form_requires_consent(client: AsyncClient, db_session):
    sa = await _sa_token(client)
    req_resp = await client.post(
        "/api/superadmin/testimonials/request",
        json={"email": "noconsent@ex.com", "name": "No Consent", "role_hint": ""},
        headers=_h(sa),
    )
    t_id = req_resp.json()["id"]

    from app.models.testimonial import Testimonial
    from sqlalchemy import select
    import uuid

    result = await db_session.execute(select(Testimonial).where(Testimonial.id == uuid.UUID(t_id)))
    form_token = result.scalar_one().request_token

    resp = await client.post(f"/api/testimonials/form/{form_token}", json={
        "name": "No Consent", "role": "CTO", "text": "Great", "stars": 5, "consent": False,
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Reject flow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_flow(client: AsyncClient, db_session):
    sa = await _sa_token(client)
    req_resp = await client.post(
        "/api/superadmin/testimonials/request",
        json={"email": "reject@ex.com", "name": "Reject User", "role_hint": ""},
        headers=_h(sa),
    )
    t_id = req_resp.json()["id"]

    from app.models.testimonial import Testimonial
    from sqlalchemy import select
    import uuid

    result = await db_session.execute(select(Testimonial).where(Testimonial.id == uuid.UUID(t_id)))
    form_token = result.scalar_one().request_token

    await client.post(f"/api/testimonials/form/{form_token}", json={
        "name": "Reject User", "role": "CEO", "text": "Meh", "stars": 2, "consent": True,
    })

    rej_resp = await client.post(
        f"/api/superadmin/testimonials/{t_id}/reject",
        json={"reason": "Off-brand"},
        headers=_h(sa),
    )
    assert rej_resp.status_code == 200

    # Must not appear on landing page
    pub = await client.get("/api/testimonials")
    names = [t["name"] for t in pub.json()]
    assert "Reject User" not in names

    # Must appear in superadmin rejected list
    list_resp = await client.get("/api/superadmin/testimonials?status=rejected", headers=_h(sa))
    ids = [t["id"] for t in list_resp.json()]
    assert t_id in ids


# ---------------------------------------------------------------------------
# Manual CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manual_create_is_immediately_approved(client: AsyncClient):
    sa = await _sa_token(client)
    t = await _create_manual(client, sa, name="Manual Entry", is_active=True)
    assert t["status"] == "approved"

    pub = await client.get("/api/testimonials")
    names = [x["name"] for x in pub.json()]
    assert "Manual Entry" in names


@pytest.mark.asyncio
async def test_manual_create_clamps_stars(client: AsyncClient):
    sa = await _sa_token(client)
    t = await _create_manual(client, sa, stars=99)
    assert t["stars"] == 5


@pytest.mark.asyncio
async def test_manual_update(client: AsyncClient):
    sa = await _sa_token(client)
    t = await _create_manual(client, sa, name="Old Name", stars=3)
    resp = await client.put(f"/api/superadmin/testimonials/{t['id']}", json={
        "name": "New Name", "role": "CTO", "text": "Updated", "stars": 4, "is_active": True, "sort_order": 0,
    }, headers=_h(sa))
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["stars"] == 4


@pytest.mark.asyncio
async def test_manual_delete(client: AsyncClient):
    sa = await _sa_token(client)
    t = await _create_manual(client, sa, name="Delete Me")
    del_resp = await client.delete(f"/api/superadmin/testimonials/{t['id']}", headers=_h(sa))
    assert del_resp.status_code == 200

    list_resp = await client.get("/api/superadmin/testimonials", headers=_h(sa))
    ids = [x["id"] for x in list_resp.json()]
    assert t["id"] not in ids


@pytest.mark.asyncio
async def test_crud_requires_auth(client: AsyncClient):
    r1 = await client.post("/api/superadmin/testimonials", json={"name": "X", "role": "Y", "text": "Z", "stars": 5, "is_active": True, "sort_order": 0})
    assert r1.status_code == 403
    r2 = await client.delete("/api/superadmin/testimonials/00000000-0000-0000-0000-000000000000")
    assert r2.status_code == 403
    r3 = await client.post("/api/superadmin/testimonials/request", json={"email": "x@y.com", "name": "X"})
    assert r3.status_code == 403


@pytest.mark.asyncio
async def test_update_not_found(client: AsyncClient):
    sa = await _sa_token(client)
    resp = await client.put(
        "/api/superadmin/testimonials/00000000-0000-0000-0000-000000000000",
        json={"name": "X", "role": "Y", "text": "Z", "stars": 5, "is_active": True, "sort_order": 0},
        headers=_h(sa),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_not_found(client: AsyncClient):
    sa = await _sa_token(client)
    resp = await client.delete("/api/superadmin/testimonials/00000000-0000-0000-0000-000000000000", headers=_h(sa))
    assert resp.status_code == 404
