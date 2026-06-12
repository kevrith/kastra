from datetime import datetime, timezone
from decimal import Decimal

from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ITEMS = [
    {"description": "Consulting", "quantity": "10", "unit_price": "5000.00"},
]


async def _setup_invoice(client, auth_headers, sample_client_id) -> str:
    """Create an accepted quotation, convert to invoice, return invoice ID."""
    qt_resp = await client.post("/api/quotations", json={
        "client_id": sample_client_id,
        "items": _ITEMS,
    }, headers=auth_headers)
    qt_id = qt_resp.json()["data"]["id"]

    await client.patch(f"/api/quotations/{qt_id}/status", json={"status": "accepted"}, headers=auth_headers)
    conv_resp = await client.post(f"/api/quotations/{qt_id}/convert", headers=auth_headers)
    return conv_resp.json()["data"]["invoice_id"]


_ISO_NOW = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

async def test_list_invoices_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/invoices", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body


async def test_list_invoices_contains_created(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.get("/api/invoices", headers=auth_headers)
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["data"]]
    assert inv_id in ids


async def test_list_invoices_filter_payment_status(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.get("/api/invoices?payment_status=unpaid", headers=auth_headers)
    assert resp.status_code == 200
    assert all(i["payment_status"] == "unpaid" for i in resp.json()["data"])


async def test_list_invoices_filter_by_client(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/invoices?client_id={sample_client_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert all(i["client"]["id"] == sample_client_id for i in resp.json()["data"])


# ---------------------------------------------------------------------------
# Get detail
# ---------------------------------------------------------------------------

async def test_get_invoice(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/invoices/{inv_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == inv_id
    assert data["payment_status"] == "unpaid"
    assert data["payment_detail"] is None
    assert len(data["items"]) == 1


async def test_get_invoice_totals(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    """10 × 5000 = 50000 subtotal, 8000 vat, 58000 grand."""
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/invoices/{inv_id}", headers=auth_headers)
    data = resp.json()["data"]
    assert Decimal(data["subtotal"]) == Decimal("50000.00")
    assert Decimal(data["vat_amount"]) == Decimal("8000.00")
    assert Decimal(data["grand_total"]) == Decimal("58000.00")


async def test_get_invoice_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/invoices/INV-9999-999", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Mark paid
# ---------------------------------------------------------------------------

async def test_mark_paid_cash(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.patch(f"/api/invoices/{inv_id}/mark-paid", json={
        "payment_method": "cash",
        "payment_date": _ISO_NOW,
        "notes": "Paid at office",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["payment_status"] == "paid"
    assert data["payment_method"] == "cash"
    assert data["payment_detail"] is not None
    assert data["payment_detail"]["payment_method"] == "cash"
    assert data["payment_detail"]["notes"] == "Paid at office"


async def test_mark_paid_bank_transfer(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.patch(f"/api/invoices/{inv_id}/mark-paid", json={
        "payment_method": "bank",
        "payment_date": _ISO_NOW,
        "transaction_id": "TXN-ABC-123",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["payment_detail"]["transaction_id"] == "TXN-ABC-123"


async def test_mark_paid_mpesa_with_receipt(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.patch(f"/api/invoices/{inv_id}/mark-paid", json={
        "payment_method": "mpesa",
        "payment_date": _ISO_NOW,
        "mpesa_receipt_number": "QHR6XXXXXXX",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["payment_detail"]["mpesa_receipt_number"] == "QHR6XXXXXXX"


async def test_cannot_mark_paid_twice(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    payload = {"payment_method": "cash", "payment_date": _ISO_NOW}
    await client.patch(f"/api/invoices/{inv_id}/mark-paid", json=payload, headers=auth_headers)
    resp = await client.patch(f"/api/invoices/{inv_id}/mark-paid", json=payload, headers=auth_headers)
    assert resp.status_code == 400


async def test_mark_paid_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.patch("/api/invoices/INV-9999-999/mark-paid", json={
        "payment_method": "cash",
        "payment_date": _ISO_NOW,
    }, headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Send reminder
# ---------------------------------------------------------------------------

async def test_send_reminder_returns_whatsapp_url(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.post(f"/api/invoices/{inv_id}/remind", headers=auth_headers)
    assert resp.status_code == 200
    message = resp.json()["message"]
    assert message.startswith("https://wa.me/")
    assert inv_id in message


async def test_send_reminder_increments_counter(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/remind", headers=auth_headers)
    await client.post(f"/api/invoices/{inv_id}/remind", headers=auth_headers)
    resp = await client.get(f"/api/invoices/{inv_id}", headers=auth_headers)
    assert resp.json()["data"]["reminders_sent"] == 2


async def test_send_reminder_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/invoices/INV-9999-999/remind", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Client history updates after invoice
# ---------------------------------------------------------------------------

async def test_client_history_reflects_invoice(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/clients/{sample_client_id}/history", headers=auth_headers)
    stats = resp.json()["data"]
    assert stats["invoice_count"] == 1
    assert stats["unpaid_count"] == 1
    assert stats["paid_count"] == 0
    assert Decimal(stats["total_billed"]) == Decimal("58000.00")


async def test_client_history_after_payment(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    await client.patch(f"/api/invoices/{inv_id}/mark-paid", json={
        "payment_method": "cash",
        "payment_date": _ISO_NOW,
    }, headers=auth_headers)
    resp = await client.get(f"/api/clients/{sample_client_id}/history", headers=auth_headers)
    stats = resp.json()["data"]
    assert stats["paid_count"] == 1
    assert stats["unpaid_count"] == 0


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------

async def test_requires_auth_list(client: AsyncClient):
    resp = await client.get("/api/invoices")
    assert resp.status_code in (401, 403)


async def test_requires_auth_get(client: AsyncClient):
    resp = await client.get("/api/invoices/INV-2026-001")
    assert resp.status_code in (401, 403)
