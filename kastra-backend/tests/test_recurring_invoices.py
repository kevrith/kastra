"""Recurring invoice templates: CRUD, frequency validation, activation toggle."""
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient

NEXT_RUN = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
_ITEMS = [{"description": "Monthly retainer", "quantity": 1, "unit_price": 25000.0}]


async def _create_recurring(client, headers, client_id, **overrides):
    payload = {
        "client_id": client_id,
        "frequency": "monthly",
        "items": _ITEMS,
        "next_run_at": NEXT_RUN,
        **overrides,
    }
    resp = await client.post("/api/recurring", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# ── Create ───────────────────────────────────────────────────────────────────

async def test_create_recurring_invoice(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    data = await _create_recurring(client, auth_headers, sample_client_id)
    assert data["frequency"] == "monthly"
    assert data["is_active"] is True
    assert data["last_run_at"] is None
    assert data["client_name"] == "Acme Corp"
    assert data["items"][0]["description"] == "Monthly retainer"


async def test_create_accepts_every_valid_frequency(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    for freq in ("weekly", "monthly", "quarterly", "yearly"):
        data = await _create_recurring(client, auth_headers, sample_client_id, frequency=freq)
        assert data["frequency"] == freq


async def test_create_rejects_unknown_frequency(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    resp = await client.post("/api/recurring", json={
        "client_id": sample_client_id,
        "frequency": "fortnightly",
        "items": _ITEMS,
        "next_run_at": NEXT_RUN,
    }, headers=auth_headers)
    assert resp.status_code == 400


async def test_create_404s_for_unknown_client(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/recurring", json={
        "client_id": "00000000-0000-0000-0000-000000000000",
        "frequency": "monthly",
        "items": _ITEMS,
        "next_run_at": NEXT_RUN,
    }, headers=auth_headers)
    assert resp.status_code == 404


async def test_create_requires_auth(client: AsyncClient, sample_client_id: str):
    resp = await client.post("/api/recurring", json={
        "client_id": sample_client_id, "frequency": "monthly",
        "items": _ITEMS, "next_run_at": NEXT_RUN,
    })
    assert resp.status_code in (401, 403)


# ── List ─────────────────────────────────────────────────────────────────────

async def test_list_recurring_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/recurring", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_recurring_ordered_by_next_run(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    later = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    sooner = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    await _create_recurring(client, auth_headers, sample_client_id, next_run_at=later)
    await _create_recurring(client, auth_headers, sample_client_id, next_run_at=sooner)

    rows = (await client.get("/api/recurring", headers=auth_headers)).json()
    runs = [r["next_run_at"] for r in rows]
    assert runs == sorted(runs)


# ── Toggle ───────────────────────────────────────────────────────────────────

async def test_toggle_pauses_and_resumes(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    rec = await _create_recurring(client, auth_headers, sample_client_id)

    paused = await client.patch(f"/api/recurring/{rec['id']}/toggle", headers=auth_headers)
    assert paused.status_code == 200
    assert paused.json()["data"]["is_active"] is False

    resumed = await client.patch(f"/api/recurring/{rec['id']}/toggle", headers=auth_headers)
    assert resumed.json()["data"]["is_active"] is True


async def test_toggle_404s_for_unknown_id(client: AsyncClient, auth_headers: dict):
    resp = await client.patch(
        "/api/recurring/00000000-0000-0000-0000-000000000000/toggle", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Delete ───────────────────────────────────────────────────────────────────

async def test_delete_recurring(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    rec = await _create_recurring(client, auth_headers, sample_client_id)
    resp = await client.delete(f"/api/recurring/{rec['id']}", headers=auth_headers)
    assert resp.status_code == 200

    rows = (await client.get("/api/recurring", headers=auth_headers)).json()
    assert rec["id"] not in [r["id"] for r in rows]


async def test_delete_404s_for_unknown_id(client: AsyncClient, auth_headers: dict):
    resp = await client.delete(
        "/api/recurring/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_recurring_is_scoped_to_the_org(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict, sample_client_id: str
):
    await _create_recurring(client, auth_headers, sample_client_id)
    assert (await client.get("/api/recurring", headers=other_org_headers)).json() == []


async def test_another_org_cannot_toggle_your_recurring(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict, sample_client_id: str
):
    rec = await _create_recurring(client, auth_headers, sample_client_id)
    resp = await client.patch(f"/api/recurring/{rec['id']}/toggle", headers=other_org_headers)
    assert resp.status_code == 404


async def test_another_org_cannot_bill_against_your_client(
    client: AsyncClient, other_org_headers: dict, sample_client_id: str
):
    resp = await client.post("/api/recurring", json={
        "client_id": sample_client_id, "frequency": "monthly",
        "items": _ITEMS, "next_run_at": NEXT_RUN,
    }, headers=other_org_headers)
    assert resp.status_code == 404
