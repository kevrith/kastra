"""Supplier directory and the RFQ flow: request → invite → supplier quotes → comparison.

Suppliers are plan-gated, so most tests here run on `paid_org_headers`.
"""
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def supplier_id(client: AsyncClient, paid_org_headers: dict) -> str:
    resp = await client.post("/api/suppliers", json={
        "name": "James Mwangi",
        "company_name": "Nairobi Hardware Ltd",
        "phone": "254712345678",
        "email": "james@hardware.co.ke",
    }, headers=paid_org_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _create_request(client, headers, **overrides):
    payload = {
        "title": "Site materials — Phase 1",
        "items": [
            {"description": "Cement 50kg", "quantity": "100", "unit": "bag"},
            {"description": "Steel bars", "quantity": "50", "unit": "pcs"},
        ],
        **overrides,
    }
    resp = await client.post("/api/suppliers/requests", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# ── Plan gating ──────────────────────────────────────────────────────────────

async def test_free_plan_cannot_add_suppliers(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/suppliers", json={"name": "Blocked"}, headers=auth_headers)
    assert resp.status_code == 402


async def test_free_plan_cannot_raise_price_requests(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/suppliers/requests", json={
        "title": "Blocked", "items": [{"description": "X"}],
    }, headers=auth_headers)
    assert resp.status_code == 402


# ── Supplier CRUD ────────────────────────────────────────────────────────────

async def test_create_supplier(client: AsyncClient, paid_org_headers: dict, supplier_id: str):
    resp = await client.get("/api/suppliers", headers=paid_org_headers)
    assert resp.status_code == 200
    sup = resp.json()[0]
    assert sup["name"] == "James Mwangi"
    assert sup["company_name"] == "Nairobi Hardware Ltd"
    assert sup["status"] == "active"


async def test_list_suppliers_search(client: AsyncClient, paid_org_headers: dict, supplier_id: str):
    await client.post("/api/suppliers", json={"name": "Zawadi Traders"}, headers=paid_org_headers)

    resp = await client.get("/api/suppliers?q=zawadi", headers=paid_org_headers)
    assert [s["name"] for s in resp.json()] == ["Zawadi Traders"]


async def test_update_supplier(client: AsyncClient, paid_org_headers: dict, supplier_id: str):
    resp = await client.put(f"/api/suppliers/{supplier_id}", json={
        "name": "James Mwangi", "company_name": "Nairobi Hardware & Co",
        "phone": "254712345678", "email": "sales@hardware.co.ke",
    }, headers=paid_org_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["company_name"] == "Nairobi Hardware & Co"


async def test_delete_supplier_hides_it_from_the_list(
    client: AsyncClient, paid_org_headers: dict, supplier_id: str
):
    resp = await client.delete(f"/api/suppliers/{supplier_id}", headers=paid_org_headers)
    assert resp.status_code == 200

    remaining = (await client.get("/api/suppliers", headers=paid_org_headers)).json()
    assert supplier_id not in [s["id"] for s in remaining]


async def test_update_unknown_supplier_404s(client: AsyncClient, paid_org_headers: dict):
    resp = await client.put("/api/suppliers/00000000-0000-0000-0000-000000000000", json={
        "name": "Ghost",
    }, headers=paid_org_headers)
    assert resp.status_code == 404


# ── Price requests (RFQs) ────────────────────────────────────────────────────

async def test_create_price_request(client: AsyncClient, paid_org_headers: dict):
    req = await _create_request(client, paid_org_headers)
    assert req["title"] == "Site materials — Phase 1"
    assert req["status"] == "open"
    assert len(req["items"]) == 2
    assert req["invites"] == []


async def test_request_items_keep_their_order(client: AsyncClient, paid_org_headers: dict):
    req = await _create_request(client, paid_org_headers)
    orders = [i["sort_order"] for i in req["items"]]
    assert orders == sorted(orders)


async def test_list_price_requests_is_paginated(client: AsyncClient, paid_org_headers: dict):
    await _create_request(client, paid_org_headers)
    resp = await client.get("/api/suppliers/requests", headers=paid_org_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["items_count"] == 2
    assert body["data"][0]["responses_count"] == 0


async def test_get_price_request(client: AsyncClient, paid_org_headers: dict):
    req = await _create_request(client, paid_org_headers)
    resp = await client.get(f"/api/suppliers/requests/{req['id']}", headers=paid_org_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == req["id"]


async def test_get_unknown_price_request_404s(client: AsyncClient, paid_org_headers: dict):
    resp = await client.get(
        "/api/suppliers/requests/00000000-0000-0000-0000-000000000000", headers=paid_org_headers
    )
    assert resp.status_code == 404


async def test_update_price_request_replaces_its_items(
    client: AsyncClient, paid_org_headers: dict
):
    req = await _create_request(client, paid_org_headers)
    resp = await client.put(f"/api/suppliers/requests/{req['id']}", json={
        "title": "Site materials — revised",
        "items": [{"description": "Ballast", "quantity": "20", "unit": "tonne"}],
    }, headers=paid_org_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "Site materials — revised"
    assert [i["description"] for i in data["items"]] == ["Ballast"]


async def test_close_price_request(client: AsyncClient, paid_org_headers: dict):
    req = await _create_request(client, paid_org_headers)
    resp = await client.patch(
        f"/api/suppliers/requests/{req['id']}/close", headers=paid_org_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "closed"


async def test_delete_price_request(client: AsyncClient, paid_org_headers: dict):
    req = await _create_request(client, paid_org_headers)
    resp = await client.delete(f"/api/suppliers/requests/{req['id']}", headers=paid_org_headers)
    assert resp.status_code == 200

    listing = (await client.get("/api/suppliers/requests", headers=paid_org_headers)).json()
    assert listing["meta"]["total"] == 0


# ── Invites ──────────────────────────────────────────────────────────────────

async def test_invite_a_supplier_mints_a_portal_link(
    client: AsyncClient, paid_org_headers: dict, supplier_id: str
):
    req = await _create_request(client, paid_org_headers)
    resp = await client.post(f"/api/suppliers/requests/{req['id']}/invites", json={
        "supplier_id": supplier_id,
    }, headers=paid_org_headers)
    assert resp.status_code == 201, resp.text
    invite = resp.json()["data"]
    assert invite["status"] == "pending"
    assert invite["supplier_name"] == "James Mwangi"
    assert invite["portal_token"] in invite["portal_url"]


async def test_inviting_the_same_supplier_twice_is_rejected(
    client: AsyncClient, paid_org_headers: dict, supplier_id: str
):
    req = await _create_request(client, paid_org_headers)
    await client.post(f"/api/suppliers/requests/{req['id']}/invites",
                      json={"supplier_id": supplier_id}, headers=paid_org_headers)
    second = await client.post(f"/api/suppliers/requests/{req['id']}/invites",
                               json={"supplier_id": supplier_id}, headers=paid_org_headers)
    assert second.status_code == 400


async def test_inviting_an_unknown_supplier_404s(client: AsyncClient, paid_org_headers: dict):
    req = await _create_request(client, paid_org_headers)
    resp = await client.post(f"/api/suppliers/requests/{req['id']}/invites", json={
        "supplier_id": "00000000-0000-0000-0000-000000000000",
    }, headers=paid_org_headers)
    assert resp.status_code == 404


async def test_remove_an_invite(
    client: AsyncClient, paid_org_headers: dict, supplier_id: str
):
    req = await _create_request(client, paid_org_headers)
    invite = (await client.post(f"/api/suppliers/requests/{req['id']}/invites",
                                json={"supplier_id": supplier_id},
                                headers=paid_org_headers)).json()["data"]

    resp = await client.delete(
        f"/api/suppliers/requests/{req['id']}/invites/{invite['id']}", headers=paid_org_headers
    )
    assert resp.status_code == 200

    detail = (await client.get(f"/api/suppliers/requests/{req['id']}",
                               headers=paid_org_headers)).json()["data"]
    assert detail["invites"] == []


# ── Supplier portal + comparison ─────────────────────────────────────────────

async def test_supplier_can_read_the_request_from_the_public_portal(
    client: AsyncClient, paid_org_headers: dict, supplier_id: str
):
    req = await _create_request(client, paid_org_headers)
    invite = (await client.post(f"/api/suppliers/requests/{req['id']}/invites",
                                json={"supplier_id": supplier_id},
                                headers=paid_org_headers)).json()["data"]

    # No auth header — the token is the credential.
    resp = await client.get(f"/api/supplier-portal/{invite['portal_token']}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "Site materials — Phase 1"
    assert body["supplier"]["name"] == "James Mwangi"
    assert len(body["items"]) == 2
    assert body["status"] == "pending"


async def test_portal_rejects_an_unknown_token(client: AsyncClient):
    resp = await client.get("/api/supplier-portal/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_supplier_submission_shows_up_in_the_comparison(
    client: AsyncClient, paid_org_headers: dict, supplier_id: str
):
    req = await _create_request(client, paid_org_headers)
    invite = (await client.post(f"/api/suppliers/requests/{req['id']}/invites",
                                json={"supplier_id": supplier_id},
                                headers=paid_org_headers)).json()["data"]

    submit = await client.post(f"/api/supplier-portal/{invite['portal_token']}/submit", json={
        "items": [
            {"description": "Cement 50kg", "quantity": "100", "unit": "bag", "unit_price": "750"},
            {"description": "Steel bars", "quantity": "50", "unit": "pcs", "unit_price": "1200"},
        ],
        "supplier_notes": "Delivery in 3 days.",
    })
    assert submit.status_code == 200, submit.text

    comparison = await client.get(
        f"/api/suppliers/requests/{req['id']}/comparison", headers=paid_org_headers
    )
    assert comparison.status_code == 200
    body = comparison.json()
    assert body["suppliers"] == ["James Mwangi"]
    # 100 × 750 + 50 × 1200 = 135,000
    assert float(body["totals"]["James Mwangi"]) == 135000.0
    cement = next(r for r in body["rows"] if r["description"] == "Cement 50kg")
    assert float(cement["prices"]["James Mwangi"]) == 750.0


async def test_comparison_is_empty_before_anyone_responds(
    client: AsyncClient, paid_org_headers: dict, supplier_id: str
):
    req = await _create_request(client, paid_org_headers)
    await client.post(f"/api/suppliers/requests/{req['id']}/invites",
                      json={"supplier_id": supplier_id}, headers=paid_org_headers)

    body = (await client.get(f"/api/suppliers/requests/{req['id']}/comparison",
                             headers=paid_org_headers)).json()
    assert body["suppliers"] == []
    assert all(r["prices"] == {} for r in body["rows"])


async def test_a_submission_marks_the_invite_responded(
    client: AsyncClient, paid_org_headers: dict, supplier_id: str
):
    req = await _create_request(client, paid_org_headers)
    invite = (await client.post(f"/api/suppliers/requests/{req['id']}/invites",
                                json={"supplier_id": supplier_id},
                                headers=paid_org_headers)).json()["data"]
    await client.post(f"/api/supplier-portal/{invite['portal_token']}/submit", json={
        "items": [{"description": "Cement 50kg", "quantity": "100", "unit_price": "750"}],
    })

    listing = (await client.get("/api/suppliers/requests", headers=paid_org_headers)).json()
    assert listing["data"][0]["responses_count"] == 1


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_suppliers_are_scoped_to_the_org(
    client: AsyncClient, paid_org_headers: dict, other_org_headers: dict, supplier_id: str
):
    resp = await client.get("/api/suppliers", headers=other_org_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_another_org_cannot_read_your_price_request(
    client: AsyncClient, paid_org_headers: dict, other_org_headers: dict
):
    req = await _create_request(client, paid_org_headers)
    resp = await client.get(f"/api/suppliers/requests/{req['id']}", headers=other_org_headers)
    assert resp.status_code == 404


async def test_another_org_cannot_see_your_comparison(
    client: AsyncClient, paid_org_headers: dict, other_org_headers: dict
):
    req = await _create_request(client, paid_org_headers)
    resp = await client.get(
        f"/api/suppliers/requests/{req['id']}/comparison", headers=other_org_headers
    )
    assert resp.status_code == 404
