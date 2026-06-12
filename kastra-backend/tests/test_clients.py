from httpx import AsyncClient


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def test_create_client(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/clients", json={
        "name": "Beta Ltd",
        "email": "beta@example.com",
        "phone": "254722000002",
        "address": "Mombasa, Kenya",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "Beta Ltd"
    assert data["email"] == "beta@example.com"
    assert data["status"] == "active"
    assert "id" in data


async def test_list_clients_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/clients", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["page"] == 1


async def test_list_clients_contains_created(client: AsyncClient, auth_headers: dict):
    await client.post("/api/clients", json={"name": "Gamma Inc"}, headers=auth_headers)
    resp = await client.get("/api/clients", headers=auth_headers)
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()["data"]]
    assert "Gamma Inc" in names


async def test_list_clients_search(client: AsyncClient, auth_headers: dict):
    await client.post("/api/clients", json={"name": "SearchMe Corp"}, headers=auth_headers)
    await client.post("/api/clients", json={"name": "OtherCo"}, headers=auth_headers)
    resp = await client.get("/api/clients?search=SearchMe", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "SearchMe Corp"


async def test_list_clients_status_filter(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post("/api/clients", json={"name": "InactiveCo"}, headers=auth_headers)
    cid = create_resp.json()["data"]["id"]
    await client.put(f"/api/clients/{cid}", json={"status": "inactive"}, headers=auth_headers)

    resp = await client.get("/api/clients?status=inactive", headers=auth_headers)
    assert resp.status_code == 200
    statuses = [c["status"] for c in resp.json()["data"]]
    assert all(s == "inactive" for s in statuses)


async def test_get_client(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    resp = await client.get(f"/api/clients/{sample_client_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == sample_client_id
    assert data["name"] == "Acme Corp"


async def test_get_client_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/clients/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_update_client_name(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    resp = await client.put(f"/api/clients/{sample_client_id}", json={
        "name": "Acme Corporation",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Acme Corporation"


async def test_update_client_status(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    resp = await client.put(f"/api/clients/{sample_client_id}", json={
        "status": "inactive",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "inactive"


async def test_update_client_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.put(f"/api/clients/{fake_id}", json={"name": "X"}, headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_client(client: AsyncClient, auth_headers: dict):
    create_resp = await client.post("/api/clients", json={"name": "ToDelete Ltd"}, headers=auth_headers)
    cid = create_resp.json()["data"]["id"]
    del_resp = await client.delete(f"/api/clients/{cid}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert "deleted" in del_resp.json()["message"].lower()

    get_resp = await client.get(f"/api/clients/{cid}", headers=auth_headers)
    assert get_resp.status_code == 404


async def test_delete_client_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/clients/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_client_history_empty(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    resp = await client.get(f"/api/clients/{sample_client_id}/history", headers=auth_headers)
    assert resp.status_code == 200
    stats = resp.json()["data"]
    assert stats["invoice_count"] == 0
    assert float(stats["total_billed"]) == 0.0
    assert stats["paid_count"] == 0
    assert stats["unpaid_count"] == 0


async def test_client_history_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/clients/{fake_id}/history", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Phone validation
# ---------------------------------------------------------------------------

async def test_phone_auto_converts_07xx(client: AsyncClient, auth_headers: dict):
    """07XX format should be auto-converted to 254XX."""
    resp = await client.post("/api/clients", json={
        "name": "PhoneCo",
        "phone": "0712345678",
    }, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["data"]["phone"] == "254712345678"


async def test_phone_accepts_254_format(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/clients", json={
        "name": "PhoneCo2",
        "phone": "254733000000",
    }, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["data"]["phone"] == "254733000000"


async def test_phone_strips_plus_prefix(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/clients", json={
        "name": "PhoneCo3",
        "phone": "+254733000001",
    }, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["data"]["phone"] == "254733000001"


async def test_phone_rejects_too_short(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/clients", json={
        "name": "PhoneBad",
        "phone": "07123",
    }, headers=auth_headers)
    assert resp.status_code == 422


async def test_phone_rejects_non_digits(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/clients", json={
        "name": "PhoneBad2",
        "phone": "abcdefghij",
    }, headers=auth_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------

async def test_requires_auth_list(client: AsyncClient):
    resp = await client.get("/api/clients")
    assert resp.status_code in (401, 403)


async def test_requires_auth_create(client: AsyncClient):
    resp = await client.post("/api/clients", json={"name": "X"})
    assert resp.status_code in (401, 403)
