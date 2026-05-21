from decimal import Decimal

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ITEMS_SIMPLE = [
    {"description": "Web design", "quantity": "5", "unit_price": "10000.00"},
]

_ITEMS_MULTI = [
    {"description": "Logo design", "quantity": "1", "unit_price": "15000.00"},
    {"description": "Branding kit", "quantity": "2", "unit_price": "8000.00"},
]


async def _create_quotation(client, auth_headers, client_id, items=None, notes=None):
    payload = {"client_id": client_id, "items": items or _ITEMS_SIMPLE}
    if notes:
        payload["notes"] = notes
    resp = await client.post("/api/quotations", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def _accept_quotation(client, auth_headers, qt_id):
    resp = await client.patch(
        f"/api/quotations/{qt_id}/status",
        json={"status": "accepted"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

async def test_create_quotation_returns_201(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    resp = await client.post("/api/quotations", json={
        "client_id": sample_client_id,
        "items": _ITEMS_SIMPLE,
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["status"] == "draft"
    assert data["client_id"] == sample_client_id
    assert len(data["items"]) == 1


async def test_quotation_id_format(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    """ID should match QT-YYYY-XXX."""
    data = await _create_quotation(client, auth_headers, sample_client_id)
    import re
    assert re.match(r"^QT-\d{4}-\d{3}$", data["id"])


async def test_vat_calculation_single_item(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    """qty=5, price=10000 → subtotal=50000, vat=8000, grand=58000."""
    data = await _create_quotation(client, auth_headers, sample_client_id, items=[
        {"description": "Service", "quantity": "5", "unit_price": "10000.00"},
    ])
    assert Decimal(data["subtotal"]) == Decimal("50000.00")
    assert Decimal(data["vat_amount"]) == Decimal("8000.00")
    assert Decimal(data["grand_total"]) == Decimal("58000.00")


async def test_vat_calculation_multi_item(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    """Logo(1×15000) + Branding(2×8000) = 31000 subtotal, 4960 vat, 35960 grand."""
    data = await _create_quotation(client, auth_headers, sample_client_id, items=_ITEMS_MULTI)
    assert Decimal(data["subtotal"]) == Decimal("31000.00")
    assert Decimal(data["vat_amount"]) == Decimal("4960.00")
    assert Decimal(data["grand_total"]) == Decimal("35960.00")


async def test_create_quotation_with_notes(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    data = await _create_quotation(client, auth_headers, sample_client_id, notes="30-day payment terms")
    assert data["notes"] == "30-day payment terms"


async def test_create_quotation_invalid_client(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/quotations", json={
        "client_id": "00000000-0000-0000-0000-000000000000",
        "items": _ITEMS_SIMPLE,
    }, headers=auth_headers)
    assert resp.status_code == 404


async def test_create_quotation_zero_quantity_rejected(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    resp = await client.post("/api/quotations", json={
        "client_id": sample_client_id,
        "items": [{"description": "Bad item", "quantity": "0", "unit_price": "100.00"}],
    }, headers=auth_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def test_list_quotations(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    await _create_quotation(client, auth_headers, sample_client_id)
    resp = await client.get("/api/quotations", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) >= 1
    assert body["meta"]["total"] >= 1


async def test_list_quotations_filter_by_status(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    data = await _create_quotation(client, auth_headers, sample_client_id)
    await client.patch(
        f"/api/quotations/{data['id']}/status",
        json={"status": "pending"},
        headers=auth_headers,
    )
    resp = await client.get("/api/quotations?status=pending", headers=auth_headers)
    assert resp.status_code == 200
    assert all(q["status"] == "pending" for q in resp.json()["data"])


async def test_list_quotations_filter_by_client(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    await _create_quotation(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/quotations?client_id={sample_client_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert all(q["client"]["id"] == sample_client_id for q in resp.json()["data"])


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

async def test_get_quotation(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/quotations/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == created["id"]


async def test_get_quotation_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/quotations/QT-9999-999", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

async def test_update_quotation_replaces_items(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    resp = await client.put(f"/api/quotations/{created['id']}", json={
        "items": [
            {"description": "New service A", "quantity": "3", "unit_price": "5000.00"},
            {"description": "New service B", "quantity": "1", "unit_price": "2000.00"},
        ],
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) == 2
    descs = {i["description"] for i in data["items"]}
    assert descs == {"New service A", "New service B"}
    # 3×5000 + 1×2000 = 17000 subtotal, 2720 vat
    assert Decimal(data["subtotal"]) == Decimal("17000.00")
    assert Decimal(data["vat_amount"]) == Decimal("2720.00")


async def test_cannot_update_accepted_quotation(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    await _accept_quotation(client, auth_headers, created["id"])
    resp = await client.put(f"/api/quotations/{created['id']}", json={
        "items": _ITEMS_SIMPLE,
    }, headers=auth_headers)
    assert resp.status_code == 400


async def test_cannot_update_declined_quotation(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    await client.patch(f"/api/quotations/{created['id']}/status", json={"status": "declined"}, headers=auth_headers)
    resp = await client.put(f"/api/quotations/{created['id']}", json={"notes": "new note"}, headers=auth_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Status updates
# ---------------------------------------------------------------------------

async def test_update_status_to_pending(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    resp = await client.patch(
        f"/api/quotations/{created['id']}/status",
        json={"status": "pending"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "pending"


async def test_update_status_to_accepted(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    data = await _accept_quotation(client, auth_headers, created["id"])
    assert data["status"] == "accepted"


async def test_update_status_to_declined(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    resp = await client.patch(
        f"/api/quotations/{created['id']}/status",
        json={"status": "declined"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "declined"


async def test_invalid_status_rejected(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    resp = await client.patch(
        f"/api/quotations/{created['id']}/status",
        json={"status": "shipped"},  # not a valid status
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Convert to invoice
# ---------------------------------------------------------------------------

async def test_convert_accepted_quotation(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    await _accept_quotation(client, auth_headers, created["id"])
    resp = await client.post(f"/api/quotations/{created['id']}/convert", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["converted_to_invoice"] is True
    assert data["invoice_id"] is not None
    import re
    assert re.match(r"^INV-\d{4}-\d{3}$", data["invoice_id"])


async def test_convert_preserves_totals(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    """Invoice created from conversion should have same totals as quotation."""
    created = await _create_quotation(client, auth_headers, sample_client_id, items=_ITEMS_MULTI)
    await _accept_quotation(client, auth_headers, created["id"])
    qt_resp = await client.post(f"/api/quotations/{created['id']}/convert", headers=auth_headers)
    inv_id = qt_resp.json()["data"]["invoice_id"]

    inv_resp = await client.get(f"/api/invoices/{inv_id}", headers=auth_headers)
    assert inv_resp.status_code == 200
    inv = inv_resp.json()["data"]
    assert Decimal(inv["subtotal"]) == Decimal("31000.00")
    assert Decimal(inv["vat_amount"]) == Decimal("4960.00")
    assert Decimal(inv["grand_total"]) == Decimal("35960.00")
    assert inv["payment_status"] == "unpaid"


async def test_cannot_convert_draft_quotation(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    resp = await client.post(f"/api/quotations/{created['id']}/convert", headers=auth_headers)
    assert resp.status_code == 400


async def test_cannot_convert_pending_quotation(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    await client.patch(f"/api/quotations/{created['id']}/status", json={"status": "pending"}, headers=auth_headers)
    resp = await client.post(f"/api/quotations/{created['id']}/convert", headers=auth_headers)
    assert resp.status_code == 400


async def test_cannot_convert_twice(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    await _accept_quotation(client, auth_headers, created["id"])
    await client.post(f"/api/quotations/{created['id']}/convert", headers=auth_headers)
    resp = await client.post(f"/api/quotations/{created['id']}/convert", headers=auth_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def test_delete_draft_quotation(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    resp = await client.delete(f"/api/quotations/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    get_resp = await client.get(f"/api/quotations/{created['id']}", headers=auth_headers)
    assert get_resp.status_code == 404


async def test_cannot_delete_converted_quotation(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    created = await _create_quotation(client, auth_headers, sample_client_id)
    await _accept_quotation(client, auth_headers, created["id"])
    await client.post(f"/api/quotations/{created['id']}/convert", headers=auth_headers)
    resp = await client.delete(f"/api/quotations/{created['id']}", headers=auth_headers)
    assert resp.status_code == 400


async def test_delete_quotation_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.delete("/api/quotations/QT-9999-999", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------

async def test_requires_auth_list(client: AsyncClient):
    resp = await client.get("/api/quotations")
    assert resp.status_code in (401, 403)


async def test_requires_auth_create(client: AsyncClient, sample_client_id: str):
    resp = await client.post("/api/quotations", json={"client_id": sample_client_id, "items": _ITEMS_SIMPLE})
    assert resp.status_code in (401, 403)
