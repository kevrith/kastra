"""Reconciliation (CSV parse + confirm), debtor aging, client statements, onboarding."""
import io

from httpx import AsyncClient

_ITEMS = [
    {"description": "Consulting", "quantity": "10", "unit_price": "5000.00"},
]
# 50,000 + 16% VAT = 58,000 grand total


async def _setup_invoice(client, auth_headers, sample_client_id) -> str:
    qt_resp = await client.post("/api/quotations", json={
        "client_id": sample_client_id,
        "items": _ITEMS,
    }, headers=auth_headers)
    qt_id = qt_resp.json()["data"]["id"]
    await client.patch(f"/api/quotations/{qt_id}/status", json={"status": "accepted"}, headers=auth_headers)
    conv_resp = await client.post(f"/api/quotations/{qt_id}/convert", headers=auth_headers)
    return conv_resp.json()["data"]["invoice_id"]


def _csv_upload(content: str):
    return {"file": ("statement.csv", io.BytesIO(content.encode()), "text/csv")}


# ── Reconciliation ──────────────────────────────────────────────────────────

async def test_parse_matches_invoice_id_in_details(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    csv_text = (
        "Receipt No.,Completion Time,Details,Paid In\n"
        f"SBA1XYZ123,01-06-2026 14:33:01,Payment for {inv_id} Acme Corp,58000.00\n"
    )
    resp = await client.post("/api/reconciliation/parse", files=_csv_upload(csv_text), headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["transactions"]) == 1
    txn = body["transactions"][0]
    assert txn["suggested_invoice_id"] == inv_id
    assert txn["confidence"] == "high"
    assert txn["amount"] == 58000.0


async def test_parse_matches_exact_amount(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    csv_text = (
        "Date,Reference,Description,Amount\n"
        "2026-06-01,TX991,Funds transfer,58000.00\n"
    )
    resp = await client.post("/api/reconciliation/parse", files=_csv_upload(csv_text), headers=auth_headers)
    assert resp.status_code == 200, resp.text
    txn = resp.json()["transactions"][0]
    assert txn["suggested_invoice_id"] == inv_id
    assert txn["confidence"] == "medium"


async def test_parse_rejects_unknown_format(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/reconciliation/parse",
        files=_csv_upload("foo,bar\n1,2\n"),
        headers=auth_headers,
    )
    assert resp.status_code == 400


async def test_confirm_records_payment(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.post("/api/reconciliation/confirm", json={
        "matches": [{"invoice_id": inv_id, "amount": 58000.0, "reference": "SBA1XYZ123"}],
    }, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["recorded"] == 1

    inv = (await client.get(f"/api/invoices/{inv_id}", headers=auth_headers)).json()["data"]
    assert inv["payment_status"] == "paid"

    # Re-confirming the same reference is skipped as a duplicate
    resp = await client.post("/api/reconciliation/confirm", json={
        "matches": [{"invoice_id": inv_id, "amount": 58000.0, "reference": "SBA1XYZ123"}],
    }, headers=auth_headers)
    assert resp.json()["recorded"] == 0
    assert len(resp.json()["skipped"]) == 1


# ── Debtor aging ────────────────────────────────────────────────────────────

async def test_aging_report_shows_outstanding(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.get("/api/reports/aging", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    row = body["data"][0]
    assert row["client_name"] == "Acme Corp"
    assert row["total"] == 58000.0
    assert body["totals"]["total"] == 58000.0


async def test_aging_report_empty_when_all_paid(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": 58000.0, "method": "bank",
    }, headers=auth_headers)
    resp = await client.get("/api/reports/aging", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == []


# ── Client statement ────────────────────────────────────────────────────────

async def test_client_statement(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": 20000.0, "method": "mpesa", "reference": "QXY12",
    }, headers=auth_headers)

    resp = await client.get(f"/api/reports/statement/{sample_client_id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    stmt = resp.json()["data"]
    assert stmt["client"]["name"] == "Acme Corp"
    assert stmt["total_invoiced"] == 58000.0
    assert stmt["total_paid"] == 20000.0
    assert stmt["closing_balance"] == 38000.0
    assert len(stmt["lines"]) == 2  # invoice + payment


async def test_statement_includes_credit_notes(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    inv_id = await _setup_invoice(client, auth_headers, sample_client_id)
    await client.post("/api/credit-notes", json={
        "invoice_id": inv_id,
        "reason": "Overbilling correction",
        "items": [{"description": "Consulting", "quantity": "1", "unit_price": "5000.00"}],
    }, headers=auth_headers)

    resp = await client.get(f"/api/reports/statement/{sample_client_id}", headers=auth_headers)
    stmt = resp.json()["data"]
    assert stmt["total_credited"] == 5800.0
    assert stmt["closing_balance"] == 58000.0 - 5800.0


# ── Onboarding checklist ────────────────────────────────────────────────────

async def test_onboarding_checklist(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    resp = await client.get("/api/dashboard/onboarding", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    steps = {s["key"]: s["done"] for s in data["steps"]}
    assert steps["client"] is True       # sample client exists
    assert steps["invoice"] is False     # nothing invoiced yet
    assert data["complete"] is False
