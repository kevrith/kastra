"""Financial reports: income, per-client revenue, debtor aging, statements, CSV."""
from datetime import datetime, timezone

from httpx import AsyncClient

_ITEMS = [{"description": "Consulting", "quantity": "10", "unit_price": "5000.00"}]  # 50,000
YEAR = datetime.now(timezone.utc).year


async def _invoice(client, headers, client_id) -> tuple[str, float]:
    qt = await client.post("/api/quotations", json={
        "client_id": client_id, "items": _ITEMS,
    }, headers=headers)
    qt_id = qt.json()["data"]["id"]
    await client.patch(f"/api/quotations/{qt_id}/status", json={"status": "accepted"}, headers=headers)
    conv = await client.post(f"/api/quotations/{qt_id}/convert", headers=headers)
    inv_id = conv.json()["data"]["invoice_id"]
    summary = await client.get(f"/api/invoices/{inv_id}/payments", headers=headers)
    return inv_id, summary.json()["grand_total"]


async def _paid_invoice(client, headers, client_id) -> tuple[str, float]:
    inv_id, total = await _invoice(client, headers, client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total, "method": "bank",
    }, headers=headers)
    return inv_id, total


# ── Income ───────────────────────────────────────────────────────────────────

async def test_income_report_requires_a_year(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/reports/income", headers=auth_headers)
    assert resp.status_code == 422


async def test_income_report_is_empty_for_a_new_org(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/reports/income?year={YEAR}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == []


async def test_income_report_counts_only_paid_invoices(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _invoice(client, auth_headers, sample_client_id)  # left unpaid
    assert (await client.get(f"/api/reports/income?year={YEAR}",
                             headers=auth_headers)).json()["data"] == []

    _, total = await _paid_invoice(client, auth_headers, sample_client_id)
    rows = (await client.get(f"/api/reports/income?year={YEAR}",
                             headers=auth_headers)).json()["data"]
    assert len(rows) == 1
    assert float(rows[0]["total"]) == total
    assert rows[0]["count"] == 1
    assert rows[0]["month"] == datetime.now(timezone.utc).month


async def test_income_report_month_filter(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _paid_invoice(client, auth_headers, sample_client_id)
    this_month = datetime.now(timezone.utc).month
    other_month = 12 if this_month != 12 else 1

    hit = (await client.get(f"/api/reports/income?year={YEAR}&month={this_month}",
                            headers=auth_headers)).json()["data"]
    miss = (await client.get(f"/api/reports/income?year={YEAR}&month={other_month}",
                             headers=auth_headers)).json()["data"]
    assert len(hit) == 1
    assert miss == []


async def test_income_report_rejects_a_bad_month(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/reports/income?year={YEAR}&month=13", headers=auth_headers)
    assert resp.status_code == 422


async def test_income_report_for_another_year_is_empty(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _paid_invoice(client, auth_headers, sample_client_id)
    rows = (await client.get(f"/api/reports/income?year={YEAR - 5}",
                             headers=auth_headers)).json()["data"]
    assert rows == []


async def test_income_report_requires_auth(client: AsyncClient):
    resp = await client.get(f"/api/reports/income?year={YEAR}")
    assert resp.status_code in (401, 403)


# ── Client revenue ───────────────────────────────────────────────────────────

async def test_client_report_lists_a_client_with_no_invoices(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    rows = (await client.get("/api/reports/clients", headers=auth_headers)).json()["data"]
    assert len(rows) == 1
    assert rows[0]["name"] == "Acme Corp"
    assert float(rows[0]["total_billed"]) == 0.0
    assert rows[0]["invoice_count"] == 0


async def test_client_report_separates_billed_from_paid(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    _, total = await _invoice(client, auth_headers, sample_client_id)
    rows = (await client.get("/api/reports/clients", headers=auth_headers)).json()["data"]
    assert float(rows[0]["total_billed"]) == total
    assert rows[0]["invoice_count"] == 1
    assert rows[0]["paid_count"] == 0

    await _paid_invoice(client, auth_headers, sample_client_id)
    rows = (await client.get("/api/reports/clients", headers=auth_headers)).json()["data"]
    assert rows[0]["invoice_count"] == 2
    assert rows[0]["paid_count"] == 1


async def test_client_report_is_ordered_by_revenue(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    quiet = await client.post("/api/clients", json={"name": "Quiet Ltd"}, headers=auth_headers)
    assert quiet.status_code == 201
    await _invoice(client, auth_headers, sample_client_id)

    rows = (await client.get("/api/reports/clients", headers=auth_headers)).json()["data"]
    assert rows[0]["name"] == "Acme Corp"
    totals = [float(r["total_billed"]) for r in rows]
    assert totals == sorted(totals, reverse=True)


# ── Debtor aging ─────────────────────────────────────────────────────────────

async def test_aging_is_empty_with_nothing_outstanding(
    client: AsyncClient, auth_headers: dict
):
    body = (await client.get("/api/reports/aging", headers=auth_headers)).json()
    assert body["data"] == []
    assert body["totals"]["total"] == 0


async def test_a_fresh_invoice_sits_in_the_current_bucket(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    _, total = await _invoice(client, auth_headers, sample_client_id)
    body = (await client.get("/api/reports/aging", headers=auth_headers)).json()
    row = body["data"][0]
    assert row["client_name"] == "Acme Corp"
    assert row["current"] == total
    assert row["total"] == total
    assert row["invoice_count"] == 1
    assert body["totals"]["total"] == total


async def test_a_paid_invoice_drops_out_of_aging(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _paid_invoice(client, auth_headers, sample_client_id)
    body = (await client.get("/api/reports/aging", headers=auth_headers)).json()
    assert body["data"] == []


async def test_a_partly_paid_invoice_shows_only_the_balance(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total / 2, "method": "mpesa",
    }, headers=auth_headers)

    body = (await client.get("/api/reports/aging", headers=auth_headers)).json()
    assert body["data"][0]["total"] == total / 2


# ── Client statement ─────────────────────────────────────────────────────────

async def test_statement_for_a_client_with_no_activity(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    resp = await client.get(f"/api/reports/statement/{sample_client_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["client"]["name"] == "Acme Corp"
    assert body["lines"] == []
    assert body["closing_balance"] == 0


async def test_statement_shows_an_invoice_as_a_debit(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _invoice(client, auth_headers, sample_client_id)
    body = (await client.get(f"/api/reports/statement/{sample_client_id}",
                             headers=auth_headers)).json()["data"]
    assert body["closing_balance"] == total
    assert any(inv_id in str(line.values()) for line in body["lines"])


async def test_a_payment_clears_the_statement_balance(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    _, total = await _paid_invoice(client, auth_headers, sample_client_id)
    body = (await client.get(f"/api/reports/statement/{sample_client_id}",
                             headers=auth_headers)).json()["data"]
    assert body["closing_balance"] == 0
    assert body["total_invoiced"] == total
    # Payments count as `total_paid`; `total_credited` is credit notes only.
    assert body["total_paid"] == total
    assert body["total_credited"] == 0


async def test_statement_404s_for_an_unknown_client(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/reports/statement/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_statement_pdf_renders(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _invoice(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/reports/statement/{sample_client_id}/pdf",
                            headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


# ── CSV export ───────────────────────────────────────────────────────────────

async def test_csv_export_requires_a_year(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/reports/export/csv", headers=auth_headers)
    assert resp.status_code == 422


async def test_csv_export_headers_and_filename(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/reports/export/csv?year={YEAR}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert f"kastra-invoices-{YEAR}.csv" in resp.headers["content-disposition"]
    assert resp.text.splitlines()[0].startswith("Invoice ID,Client,Status")


async def test_csv_export_contains_the_invoice(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, _ = await _invoice(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/reports/export/csv?year={YEAR}", headers=auth_headers)
    assert inv_id in resp.text
    assert "Acme Corp" in resp.text


# ── Permission gating ────────────────────────────────────────────────────────

async def _member_headers(client, auth_headers, role: str) -> dict:
    import uuid as _uuid
    email = f"{role}-{_uuid.uuid4().hex[:10]}@example.com"
    invite = await client.post("/api/team/invite", json={
        "email": email, "role": role, "display_name": role.title(),
    }, headers=auth_headers)
    member = invite.json()
    await client.post("/api/team/accept-invite", json={
        "token": member["invite_token"], "password": "memberpass123",
    })
    login = await client.post("/api/auth/login", json={
        "email": email, "password": "memberpass123",
    })
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_a_field_agent_cannot_read_reports(client: AsyncClient, auth_headers: dict):
    headers = await _member_headers(client, auth_headers, "field_agent")
    resp = await client.get(f"/api/reports/income?year={YEAR}", headers=headers)
    assert resp.status_code == 403


async def test_a_viewer_can_read_reports(client: AsyncClient, auth_headers: dict):
    """`viewer` carries can_view_reports by default — read-only, but allowed."""
    headers = await _member_headers(client, auth_headers, "viewer")
    resp = await client.get(f"/api/reports/income?year={YEAR}", headers=headers)
    assert resp.status_code == 200


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_reports_never_include_another_orgs_revenue(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict, sample_client_id: str
):
    await _paid_invoice(client, auth_headers, sample_client_id)

    assert (await client.get(f"/api/reports/income?year={YEAR}",
                             headers=other_org_headers)).json()["data"] == []
    assert (await client.get("/api/reports/clients",
                             headers=other_org_headers)).json()["data"] == []
    assert (await client.get("/api/reports/aging",
                             headers=other_org_headers)).json()["data"] == []


async def test_another_org_cannot_pull_your_clients_statement(
    client: AsyncClient, other_org_headers: dict, sample_client_id: str
):
    resp = await client.get(f"/api/reports/statement/{sample_client_id}",
                            headers=other_org_headers)
    assert resp.status_code == 404


async def test_csv_export_never_leaks_another_orgs_invoices(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict, sample_client_id: str
):
    inv_id, _ = await _invoice(client, auth_headers, sample_client_id)
    resp = await client.get(f"/api/reports/export/csv?year={YEAR}", headers=other_org_headers)
    assert inv_id not in resp.text
