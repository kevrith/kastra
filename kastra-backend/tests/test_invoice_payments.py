"""Partial payments against an invoice: balance tracking, status transitions, reversal."""
from httpx import AsyncClient

_ITEMS = [{"description": "Consulting", "quantity": "10", "unit_price": "5000.00"}]  # 50,000 net


async def _setup_invoice(client, headers, client_id) -> tuple[str, float]:
    """Create an accepted quotation, convert it, return (invoice_id, grand_total)."""
    qt = await client.post("/api/quotations", json={
        "client_id": client_id, "items": _ITEMS,
    }, headers=headers)
    qt_id = qt.json()["data"]["id"]
    await client.patch(f"/api/quotations/{qt_id}/status", json={"status": "accepted"}, headers=headers)
    conv = await client.post(f"/api/quotations/{qt_id}/convert", headers=headers)
    inv_id = conv.json()["data"]["invoice_id"]

    summary = await client.get(f"/api/invoices/{inv_id}/payments", headers=headers)
    return inv_id, summary.json()["grand_total"]


# ── Summary ──────────────────────────────────────────────────────────────────

async def test_new_invoice_has_full_balance_due(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/invoices/{inv_id}/payments", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["amount_paid"] == 0
    assert body["balance_due"] == total
    assert body["payment_status"] == "unpaid"
    assert body["payments"] == []


async def test_payments_summary_404s_for_unknown_invoice(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/invoices/INV-NOPE/payments", headers=auth_headers)
    assert resp.status_code == 404


# ── Recording payments ───────────────────────────────────────────────────────

async def test_partial_payment_sets_status_partial(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total / 2, "method": "mpesa", "reference": "QF12ABC",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["method"] == "mpesa"

    summary = (await client.get(f"/api/invoices/{inv_id}/payments", headers=auth_headers)).json()
    assert summary["payment_status"] == "partial"
    assert summary["amount_paid"] == total / 2
    assert summary["balance_due"] == total / 2


async def test_two_partial_payments_settle_the_invoice(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _setup_invoice(client, auth_headers, sample_client_id)
    for _ in range(2):
        resp = await client.post(f"/api/invoices/{inv_id}/payments", json={
            "amount": total / 2, "method": "cash",
        }, headers=auth_headers)
        assert resp.status_code == 201, resp.text

    summary = (await client.get(f"/api/invoices/{inv_id}/payments", headers=auth_headers)).json()
    assert summary["payment_status"] == "paid"
    assert summary["balance_due"] == 0
    assert len(summary["payments"]) == 2


async def test_full_payment_sets_status_paid(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _setup_invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total, "method": "bank",
    }, headers=auth_headers)

    summary = (await client.get(f"/api/invoices/{inv_id}/payments", headers=auth_headers)).json()
    assert summary["payment_status"] == "paid"
    assert summary["balance_due"] == 0


async def test_overpayment_is_rejected(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total + 1000, "method": "cash",
    }, headers=auth_headers)
    assert resp.status_code == 400
    assert "exceeds balance" in resp.json()["detail"].lower()


async def test_zero_and_negative_payments_are_rejected(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, _ = await _setup_invoice(client, auth_headers, sample_client_id)
    for bad in (0, -500):
        resp = await client.post(f"/api/invoices/{inv_id}/payments", json={
            "amount": bad, "method": "cash",
        }, headers=auth_headers)
        assert resp.status_code == 400, f"amount={bad} should be rejected"


async def test_paying_an_already_paid_invoice_is_rejected(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _setup_invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total, "method": "cash",
    }, headers=auth_headers)

    resp = await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": 100, "method": "cash",
    }, headers=auth_headers)
    assert resp.status_code == 400
    assert "already fully paid" in resp.json()["detail"].lower()


async def test_payment_on_unknown_invoice_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/invoices/INV-NOPE/payments", json={
        "amount": 10, "method": "cash",
    }, headers=auth_headers)
    assert resp.status_code == 404


# ── Full payment notifies the owner ──────────────────────────────────────────

async def test_full_payment_raises_a_notification(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _setup_invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total, "method": "mpesa",
    }, headers=auth_headers)

    notes = (await client.get("/api/notifications", headers=auth_headers)).json()
    payment_notes = [n for n in notes["items"] if n["type"] == "payment_received"]
    assert payment_notes, "a fully-paid invoice should notify the owner"
    assert payment_notes[0]["entity_id"] == inv_id


async def test_partial_payment_does_not_notify(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _setup_invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total / 4, "method": "cash",
    }, headers=auth_headers)

    notes = (await client.get("/api/notifications", headers=auth_headers)).json()
    assert not [n for n in notes["items"] if n["type"] == "payment_received"]


# ── Reversal ─────────────────────────────────────────────────────────────────

async def test_deleting_a_payment_restores_the_balance(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _setup_invoice(client, auth_headers, sample_client_id)
    pay = await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total, "method": "cash",
    }, headers=auth_headers)
    payment_id = pay.json()["data"]["id"]

    resp = await client.delete(f"/api/invoices/{inv_id}/payments/{payment_id}", headers=auth_headers)
    assert resp.status_code == 200

    summary = (await client.get(f"/api/invoices/{inv_id}/payments", headers=auth_headers)).json()
    assert summary["payment_status"] == "unpaid"
    assert summary["amount_paid"] == 0
    assert summary["balance_due"] == total


async def test_deleting_one_of_two_payments_leaves_it_partial(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _setup_invoice(client, auth_headers, sample_client_id)
    first = await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total / 2, "method": "cash",
    }, headers=auth_headers)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total / 2, "method": "cash",
    }, headers=auth_headers)

    await client.delete(
        f"/api/invoices/{inv_id}/payments/{first.json()['data']['id']}", headers=auth_headers
    )
    summary = (await client.get(f"/api/invoices/{inv_id}/payments", headers=auth_headers)).json()
    assert summary["payment_status"] == "partial"
    assert summary["amount_paid"] == total / 2


async def test_deleting_an_unknown_payment_404s(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, _ = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.delete(
        f"/api/invoices/{inv_id}/payments/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_another_org_cannot_see_your_payments(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict, sample_client_id: str
):
    inv_id, _ = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/invoices/{inv_id}/payments", headers=other_org_headers)
    assert resp.status_code == 404


async def test_another_org_cannot_record_a_payment_on_your_invoice(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict, sample_client_id: str
):
    inv_id, _ = await _setup_invoice(client, auth_headers, sample_client_id)
    resp = await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": 100, "method": "cash",
    }, headers=other_org_headers)
    assert resp.status_code == 404
