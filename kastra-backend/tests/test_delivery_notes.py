"""Delivery notes: creation from invoice, item copying, status updates."""
from httpx import AsyncClient

_ITEMS = [
    {"description": "Cement bags", "quantity": "40", "unit_price": "850.00"},
    {"description": "Steel bars", "quantity": "12", "unit_price": "1200.00"},
]


async def _setup_invoice(client, auth_headers, sample_client_id) -> str:
    qt_resp = await client.post("/api/quotations", json={
        "client_id": sample_client_id,
        "items": _ITEMS,
    }, headers=auth_headers)
    qt_id = qt_resp.json()["data"]["id"]
    await client.patch(f"/api/quotations/{qt_id}/status", json={"status": "accepted"}, headers=auth_headers)
    conv_resp = await client.post(f"/api/quotations/{qt_id}/convert", headers=auth_headers)
    return conv_resp.json()["data"]["invoice_id"]


async def test_create_delivery_note_from_invoice(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.post("/api/delivery-notes", json={
        "invoice_id": inv_id,
        "driver_name": "John Mwangi",
        "vehicle_reg": "KDA 123A",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    dn = resp.json()["data"]
    assert "-DN-" in dn["id"]
    assert dn["invoice_id"] == inv_id
    assert dn["status"] == "issued"
    # Items copied from the invoice
    assert len(dn["items"]) == 2
    descriptions = {i["description"] for i in dn["items"]}
    assert descriptions == {"Cement bags", "Steel bars"}


async def test_delivery_note_requires_source_or_client(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/delivery-notes", json={
        "driver_name": "John",
    }, headers=auth_headers)
    assert resp.status_code == 400


async def test_mark_delivered(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    dn_id = (await client.post("/api/delivery-notes", json={"invoice_id": inv_id}, headers=auth_headers)).json()["data"]["id"]

    resp = await client.patch(f"/api/delivery-notes/{dn_id}", json={
        "status": "delivered",
        "received_by": "Jane at Acme",
    }, headers=auth_headers)
    assert resp.status_code == 200
    dn = resp.json()["data"]
    assert dn["status"] == "delivered"
    assert dn["received_by"] == "Jane at Acme"


async def test_delete_delivery_note(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    dn_id = (await client.post("/api/delivery-notes", json={"invoice_id": inv_id}, headers=auth_headers)).json()["data"]["id"]
    resp = await client.delete(f"/api/delivery-notes/{dn_id}", headers=auth_headers)
    assert resp.status_code == 200
    resp = await client.get(f"/api/delivery-notes/{dn_id}", headers=auth_headers)
    assert resp.status_code == 404
