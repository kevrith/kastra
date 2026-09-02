"""Product catalogue: CRUD, search, client-specific pricing, org isolation."""
from httpx import AsyncClient


async def _create_product(client, headers, **overrides):
    payload = {"name": "Cement 50kg", "unit_price": 750.0, "cost_price": 600.0, **overrides}
    resp = await client.post("/api/products", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# ── Create ───────────────────────────────────────────────────────────────────

async def test_create_product(client: AsyncClient, auth_headers: dict):
    data = await _create_product(client, auth_headers)
    assert data["name"] == "Cement 50kg"
    assert data["unit_price"] == 750.0
    assert data["cost_price"] == 600.0
    assert "id" in data


async def test_create_product_defaults_cost_price_to_zero(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/products", json={
        "name": "Consultancy", "unit_price": 5000.0,
    }, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["data"]["cost_price"] == 0.0


async def test_create_product_requires_price(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/products", json={"name": "No price"}, headers=auth_headers)
    assert resp.status_code == 422


async def test_create_product_requires_auth(client: AsyncClient):
    resp = await client.post("/api/products", json={"name": "X", "unit_price": 1})
    assert resp.status_code in (401, 403)


# ── List / search ────────────────────────────────────────────────────────────

async def test_list_products_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/products", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_products_sorted_by_name(client: AsyncClient, auth_headers: dict):
    await _create_product(client, auth_headers, name="Zinc sheet")
    await _create_product(client, auth_headers, name="Aggregate")
    await _create_product(client, auth_headers, name="Mortar")

    resp = await client.get("/api/products", headers=auth_headers)
    names = [p["name"] for p in resp.json()]
    assert names == sorted(names)


async def test_list_products_search_is_case_insensitive(client: AsyncClient, auth_headers: dict):
    await _create_product(client, auth_headers, name="Steel Bars")
    await _create_product(client, auth_headers, name="Timber")

    resp = await client.get("/api/products?q=steel", headers=auth_headers)
    assert resp.status_code == 200
    assert [p["name"] for p in resp.json()] == ["Steel Bars"]


async def test_list_products_client_price_is_null_without_agreement(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _create_product(client, auth_headers, name="Paint 20L")
    resp = await client.get(f"/api/products?client_id={sample_client_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()[0]["client_price"] is None


# ── Update ───────────────────────────────────────────────────────────────────

async def test_update_product(client: AsyncClient, auth_headers: dict):
    prod = await _create_product(client, auth_headers)
    resp = await client.put(f"/api/products/{prod['id']}", json={
        "name": "Cement 50kg (Bamburi)", "unit_price": 800.0, "cost_price": 650.0,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "Cement 50kg (Bamburi)"
    assert data["unit_price"] == 800.0


async def test_update_missing_product_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.put("/api/products/00000000-0000-0000-0000-000000000000", json={
        "name": "Ghost", "unit_price": 1.0,
    }, headers=auth_headers)
    assert resp.status_code == 404


# ── Delete ───────────────────────────────────────────────────────────────────

async def test_delete_product_removes_it_from_the_list(client: AsyncClient, auth_headers: dict):
    prod = await _create_product(client, auth_headers, name="Temporary")
    resp = await client.delete(f"/api/products/{prod['id']}", headers=auth_headers)
    assert resp.status_code == 200

    listing = await client.get("/api/products", headers=auth_headers)
    assert prod["id"] not in [p["id"] for p in listing.json()]


async def test_delete_missing_product_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.delete(
        "/api/products/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_products_are_scoped_to_the_org(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    await _create_product(client, auth_headers, name="Private Stock")
    resp = await client.get("/api/products", headers=other_org_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_another_org_cannot_update_your_product(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    prod = await _create_product(client, auth_headers)
    resp = await client.put(f"/api/products/{prod['id']}", json={
        "name": "Hijacked", "unit_price": 1.0,
    }, headers=other_org_headers)
    assert resp.status_code == 404


async def test_another_org_cannot_delete_your_product(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    prod = await _create_product(client, auth_headers)
    resp = await client.delete(f"/api/products/{prod['id']}", headers=other_org_headers)
    assert resp.status_code == 404
