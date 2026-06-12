"""Credit notes: creation, balance application, over-credit guard, voiding."""
from httpx import AsyncClient

_ITEMS = [
    {"description": "Consulting", "quantity": "10", "unit_price": "5000.00"},
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


async def _create_cn(client, auth_headers, invoice_id, quantity="2"):
    return await client.post("/api/credit-notes", json={
        "invoice_id": invoice_id,
        "reason": "Goods returned",
        "items": [{"description": "Consulting", "quantity": quantity, "unit_price": "5000.00"}],
    }, headers=auth_headers)


async def test_create_credit_note(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await _create_cn(client, auth_headers, inv_id)
    assert resp.status_code == 201, resp.text
    cn = resp.json()["data"]
    assert cn["invoice_id"] == inv_id
    assert "-CN-" in cn["id"]
    assert float(cn["subtotal"]) == 10000.0
    assert float(cn["grand_total"]) == 11600.0  # +16% VAT

    # Credit applied to the invoice balance
    inv_resp = await client.get(f"/api/invoices/{inv_id}", headers=auth_headers)
    inv = inv_resp.json()["data"]
    assert float(inv["amount_credited"]) == 11600.0
    assert inv["payment_status"] == "partial"


async def test_credit_note_requires_reason(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.post("/api/credit-notes", json={
        "invoice_id": inv_id,
        "reason": "  ",
        "items": [{"description": "Consulting", "quantity": "1", "unit_price": "5000.00"}],
    }, headers=auth_headers)
    assert resp.status_code == 422


async def test_credit_note_cannot_exceed_invoice(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await _create_cn(client, auth_headers, inv_id, quantity="50")  # way over
    assert resp.status_code == 400
    assert "exceeds" in resp.json()["detail"].lower()


async def test_full_credit_marks_invoice_paid(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await _create_cn(client, auth_headers, inv_id, quantity="10")  # full amount
    assert resp.status_code == 201, resp.text
    inv = (await client.get(f"/api/invoices/{inv_id}", headers=auth_headers)).json()["data"]
    assert inv["payment_status"] == "paid"


async def test_void_credit_note_restores_balance(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    cn_id = (await _create_cn(client, auth_headers, inv_id)).json()["data"]["id"]

    resp = await client.delete(f"/api/credit-notes/{cn_id}", headers=auth_headers)
    assert resp.status_code == 200

    inv = (await client.get(f"/api/invoices/{inv_id}", headers=auth_headers)).json()["data"]
    assert float(inv["amount_credited"]) == 0.0
    assert inv["payment_status"] == "unpaid"


async def test_list_credit_notes_by_invoice(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    await _create_cn(client, auth_headers, inv_id)
    resp = await client.get("/api/credit-notes", params={"invoice_id": inv_id}, headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
