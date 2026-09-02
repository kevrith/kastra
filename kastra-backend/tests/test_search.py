"""Global search across clients, invoices and quotations."""
from httpx import AsyncClient

_ITEMS = [{"description": "Consulting", "quantity": "1", "unit_price": "5000.00"}]


async def _make_quotation(client, headers, client_id) -> str:
    resp = await client.post("/api/quotations", json={
        "client_id": client_id, "items": _ITEMS,
    }, headers=headers)
    return resp.json()["data"]["id"]


async def _make_invoice(client, headers, client_id) -> str:
    qt_id = await _make_quotation(client, headers, client_id)
    await client.patch(f"/api/quotations/{qt_id}/status", json={"status": "accepted"}, headers=headers)
    conv = await client.post(f"/api/quotations/{qt_id}/convert", headers=headers)
    return conv.json()["data"]["invoice_id"]


# ── Query handling ───────────────────────────────────────────────────────────

async def test_search_requires_a_query(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/search", headers=auth_headers)
    assert resp.status_code == 422


async def test_search_rejects_an_empty_query(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/search?q=", headers=auth_headers)
    assert resp.status_code == 422


async def test_single_character_query_returns_nothing(client: AsyncClient, auth_headers: dict):
    """Guard against a one-letter query scanning the whole org."""
    resp = await client.get("/api/search?q=a", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_whitespace_only_query_returns_nothing(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/search?q=%20%20", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_requires_auth(client: AsyncClient):
    resp = await client.get("/api/search?q=acme")
    assert resp.status_code in (401, 403)


# ── Clients ──────────────────────────────────────────────────────────────────

async def test_search_finds_a_client_by_name(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    resp = await client.get("/api/search?q=Acme", headers=auth_headers)
    assert resp.status_code == 200
    hits = [r for r in resp.json() if r["type"] == "client"]
    assert hits and hits[0]["id"] == sample_client_id
    assert hits[0]["label"] == "Acme Corp"


async def test_search_client_is_case_insensitive(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    resp = await client.get("/api/search?q=acme", headers=auth_headers)
    assert [r["type"] for r in resp.json()].count("client") == 1


async def test_search_finds_a_client_by_email(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    resp = await client.get("/api/search?q=acme@example.com", headers=auth_headers)
    assert any(r["id"] == sample_client_id for r in resp.json())


async def test_search_finds_a_client_by_phone(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    resp = await client.get("/api/search?q=254712000001", headers=auth_headers)
    assert any(r["id"] == sample_client_id for r in resp.json())


async def test_search_caps_client_results_at_five(client: AsyncClient, auth_headers: dict):
    for i in range(7):
        await client.post("/api/clients", json={"name": f"Bulkco {i}"}, headers=auth_headers)

    resp = await client.get("/api/search?q=Bulkco", headers=auth_headers)
    assert len([r for r in resp.json() if r["type"] == "client"]) == 5


# ── Documents ────────────────────────────────────────────────────────────────

async def test_search_finds_a_quotation_by_id(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    qt_id = await _make_quotation(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/search?q={qt_id}", headers=auth_headers)
    assert resp.status_code == 200
    hits = [r for r in resp.json() if r["type"] == "quotation"]
    assert [h["id"] for h in hits] == [qt_id]


async def test_search_finds_an_invoice_by_id(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id = await _make_invoice(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/search?q={inv_id}", headers=auth_headers)
    hits = [r for r in resp.json() if r["type"] == "invoice"]
    assert [h["id"] for h in hits] == [inv_id]


async def test_search_result_carries_a_subtitle(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id = await _make_invoice(client, auth_headers, sample_client_id)
    hit = [r for r in (await client.get(f"/api/search?q={inv_id}", headers=auth_headers)).json()
           if r["type"] == "invoice"][0]
    assert "KSh" in hit["sub"]
    assert "unpaid" in hit["sub"]


async def test_search_with_no_matches_returns_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/search?q=zzzznothinghere", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_search_never_crosses_org_boundaries(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict, sample_client_id: str
):
    inv_id = await _make_invoice(client, auth_headers, sample_client_id)

    assert (await client.get("/api/search?q=Acme", headers=other_org_headers)).json() == []
    assert (await client.get(f"/api/search?q={inv_id}", headers=other_org_headers)).json() == []
