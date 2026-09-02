"""Dashboard KPIs, trends and the onboarding checklist."""
from datetime import date

from httpx import AsyncClient

_ITEMS = [{"description": "Consulting", "quantity": "10", "unit_price": "5000.00"}]  # 50,000


async def _quotation(client, headers, client_id) -> str:
    resp = await client.post("/api/quotations", json={
        "client_id": client_id, "items": _ITEMS,
    }, headers=headers)
    return resp.json()["data"]["id"]


async def _invoice(client, headers, client_id) -> tuple[str, float]:
    qt_id = await _quotation(client, headers, client_id)
    await client.patch(f"/api/quotations/{qt_id}/status", json={"status": "accepted"}, headers=headers)
    conv = await client.post(f"/api/quotations/{qt_id}/convert", headers=headers)
    inv_id = conv.json()["data"]["invoice_id"]
    summary = await client.get(f"/api/invoices/{inv_id}/payments", headers=headers)
    return inv_id, summary.json()["grand_total"]


async def _stats(client, headers) -> dict:
    resp = await client.get("/api/dashboard/stats", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── Shape ────────────────────────────────────────────────────────────────────

async def test_stats_on_a_brand_new_org(client: AsyncClient, auth_headers: dict):
    body = await _stats(client, auth_headers)
    assert body["kpis"]["pending_quotations"] == 0
    assert body["kpis"]["unpaid_invoices"] == 0
    assert float(body["kpis"]["monthly_revenue"]) == 0.0
    assert body["kpis"]["active_clients"] == 0
    assert body["top_clients"] == []
    assert body["recent_quotations"] == []
    assert body["recent_invoices"] == []


async def test_stats_returns_six_monthly_bars_and_three_years(
    client: AsyncClient, auth_headers: dict
):
    body = await _stats(client, auth_headers)
    assert len(body["monthly_bars"]) == 6
    assert len(body["yearly_trend"]) == 3
    years = [p["year"] for p in body["yearly_trend"]]
    assert years == sorted(years)


async def test_stats_requires_auth(client: AsyncClient):
    resp = await client.get("/api/dashboard/stats")
    assert resp.status_code in (401, 403)


# ── KPIs track real data ─────────────────────────────────────────────────────

async def test_active_clients_kpi(client: AsyncClient, auth_headers: dict, sample_client_id: str):
    body = await _stats(client, auth_headers)
    assert body["kpis"]["active_clients"] == 1


async def test_pending_quotations_kpi(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    qt_id = await _quotation(client, auth_headers, sample_client_id)
    await client.patch(f"/api/quotations/{qt_id}/status", json={"status": "pending"},
                       headers=auth_headers)

    body = await _stats(client, auth_headers)
    assert body["kpis"]["pending_quotations"] == 1


async def test_unpaid_invoices_kpi(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _invoice(client, auth_headers, sample_client_id)
    body = await _stats(client, auth_headers)
    assert body["kpis"]["unpaid_invoices"] == 1


async def test_paying_an_invoice_moves_it_out_of_unpaid_and_into_revenue(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total, "method": "mpesa",
    }, headers=auth_headers)

    body = await _stats(client, auth_headers)
    assert body["kpis"]["unpaid_invoices"] == 0
    assert float(body["kpis"]["monthly_revenue"]) == total


async def test_monthly_expenses_kpi(client: AsyncClient, auth_headers: dict):
    await client.post("/api/expenses", json={
        "category": "rent", "description": "Office", "amount": 30000.0,
        "date": date.today().isoformat(),
    }, headers=auth_headers)

    body = await _stats(client, auth_headers)
    assert float(body["kpis"]["monthly_expenses"]) == 30000.0


async def test_net_profit_is_revenue_minus_expenses(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total, "method": "cash",
    }, headers=auth_headers)
    await client.post("/api/expenses", json={
        "category": "materials", "description": "Supplies", "amount": 12000.0,
        "date": date.today().isoformat(),
    }, headers=auth_headers)

    body = await _stats(client, auth_headers)
    assert float(body["kpis"]["monthly_net_profit"]) == total - 12000.0


# ── Trends and recents ───────────────────────────────────────────────────────

async def test_paid_revenue_lands_in_the_current_month_bar(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, total = await _invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total, "method": "cash",
    }, headers=auth_headers)

    body = await _stats(client, auth_headers)
    assert float(body["monthly_bars"][-1]["revenue"]) == total
    assert float(body["yearly_trend"][-1]["revenue"]) == total


async def test_top_clients_lists_the_billed_client(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _invoice(client, auth_headers, sample_client_id)
    body = await _stats(client, auth_headers)
    assert body["top_clients"][0]["name"] == "Acme Corp"
    assert body["top_clients"][0]["invoice_count"] == 1


async def test_recent_lists_are_capped_at_five(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    for _ in range(6):
        await _quotation(client, auth_headers, sample_client_id)
    body = await _stats(client, auth_headers)
    assert len(body["recent_quotations"]) == 5


async def test_recent_invoice_carries_the_client_name(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv_id, _ = await _invoice(client, auth_headers, sample_client_id)
    body = await _stats(client, auth_headers)
    recent = body["recent_invoices"][0]
    assert recent["id"] == inv_id
    assert recent["client_name"] == "Acme Corp"
    assert recent["payment_status"] == "unpaid"


# ── Onboarding checklist ─────────────────────────────────────────────────────

async def test_onboarding_starts_incomplete(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/dashboard/onboarding", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["complete"] is False
    assert body["completed"] == 0
    assert body["total"] == len(body["steps"])


async def test_adding_a_client_ticks_the_client_step(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    body = (await client.get("/api/dashboard/onboarding", headers=auth_headers)).json()["data"]
    step = next(s for s in body["steps"] if s["key"] == "client")
    assert step["done"] is True
    assert body["completed"] == 1


async def test_creating_an_invoice_ticks_three_steps(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _invoice(client, auth_headers, sample_client_id)
    body = (await client.get("/api/dashboard/onboarding", headers=auth_headers)).json()["data"]
    done = {s["key"] for s in body["steps"] if s["done"]}
    assert {"client", "quotation", "invoice"} <= done


async def test_connecting_paystack_ticks_the_payments_step(
    client: AsyncClient, auth_headers: dict
):
    await client.put("/api/organization", json={
        "paystack_secret_key": "sk_test_dummy_value_for_tests",
    }, headers=auth_headers)

    body = (await client.get("/api/dashboard/onboarding", headers=auth_headers)).json()["data"]
    step = next(s for s in body["steps"] if s["key"] == "payments")
    assert step["done"] is True


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_another_orgs_revenue_never_shows_in_your_dashboard(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict, sample_client_id: str
):
    inv_id, total = await _invoice(client, auth_headers, sample_client_id)
    await client.post(f"/api/invoices/{inv_id}/payments", json={
        "amount": total, "method": "cash",
    }, headers=auth_headers)

    body = await _stats(client, other_org_headers)
    assert float(body["kpis"]["monthly_revenue"]) == 0.0
    assert body["kpis"]["active_clients"] == 0
    assert body["recent_invoices"] == []
