"""Expenses: CRUD, filters, pagination, monthly summary, org isolation."""
from datetime import date, timedelta

from httpx import AsyncClient

TODAY = date.today()


async def _create_expense(client, headers, **overrides):
    payload = {
        "category": "materials",
        "description": "Cement for slab",
        "vendor": "Nairobi Hardware",
        "amount": 12000.0,
        "date": TODAY.isoformat(),
        **overrides,
    }
    resp = await client.post("/api/expenses", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# ── Create ───────────────────────────────────────────────────────────────────

async def test_create_expense(client: AsyncClient, auth_headers: dict):
    data = await _create_expense(client, auth_headers)
    assert data["category"] == "materials"
    assert data["amount"] == 12000.0
    assert data["vendor"] == "Nairobi Hardware"
    assert data["date"] == TODAY.isoformat()


async def test_create_expense_rejects_bad_date(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/expenses", json={
        "category": "fuel", "description": "Diesel", "amount": 500.0, "date": "not-a-date",
    }, headers=auth_headers)
    assert resp.status_code == 422


async def test_create_expense_requires_auth(client: AsyncClient):
    resp = await client.post("/api/expenses", json={
        "category": "fuel", "description": "D", "amount": 1, "date": TODAY.isoformat(),
    })
    assert resp.status_code in (401, 403)


# ── List, filter, paginate ───────────────────────────────────────────────────

async def test_list_expenses_is_paginated(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/expenses", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body and "meta" in body
    assert body["meta"]["page"] == 1


async def test_list_expenses_filter_by_category(client: AsyncClient, auth_headers: dict):
    await _create_expense(client, auth_headers, category="fuel", description="Diesel")
    await _create_expense(client, auth_headers, category="rent", description="Office rent")

    resp = await client.get("/api/expenses?category=fuel", headers=auth_headers)
    assert resp.status_code == 200
    rows = resp.json()["data"]
    assert rows and all(r["category"] == "fuel" for r in rows)


async def test_list_expenses_filter_by_date_range(client: AsyncClient, auth_headers: dict):
    old = (TODAY - timedelta(days=90)).isoformat()
    await _create_expense(client, auth_headers, description="Old spend", date=old)
    await _create_expense(client, auth_headers, description="Recent spend")

    resp = await client.get(
        f"/api/expenses?from_date={(TODAY - timedelta(days=7)).isoformat()}", headers=auth_headers
    )
    assert resp.status_code == 200
    descriptions = [r["description"] for r in resp.json()["data"]]
    assert "Recent spend" in descriptions
    assert "Old spend" not in descriptions


async def test_list_expenses_respects_limit(client: AsyncClient, auth_headers: dict):
    for i in range(3):
        await _create_expense(client, auth_headers, description=f"Item {i}")

    resp = await client.get("/api/expenses?limit=2", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total"] >= 3


async def test_list_expenses_rejects_limit_over_max(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/expenses?limit=500", headers=auth_headers)
    assert resp.status_code == 422


async def test_list_expenses_newest_first(client: AsyncClient, auth_headers: dict):
    await _create_expense(client, auth_headers, description="Older", date=(TODAY - timedelta(days=5)).isoformat())
    await _create_expense(client, auth_headers, description="Newer")

    rows = (await client.get("/api/expenses", headers=auth_headers)).json()["data"]
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates, reverse=True)


# ── Update / delete ──────────────────────────────────────────────────────────

async def test_update_expense(client: AsyncClient, auth_headers: dict):
    exp = await _create_expense(client, auth_headers)
    resp = await client.put(f"/api/expenses/{exp['id']}", json={
        "category": "transport",
        "description": "Lorry hire",
        "amount": 8000.0,
        "date": TODAY.isoformat(),
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["category"] == "transport"
    assert data["amount"] == 8000.0
    assert data["vendor"] is None  # cleared — PUT replaces the whole record


async def test_update_missing_expense_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.put("/api/expenses/00000000-0000-0000-0000-000000000000", json={
        "category": "other", "description": "X", "amount": 1.0, "date": TODAY.isoformat(),
    }, headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_expense(client: AsyncClient, auth_headers: dict):
    exp = await _create_expense(client, auth_headers, description="Delete me")
    resp = await client.delete(f"/api/expenses/{exp['id']}", headers=auth_headers)
    assert resp.status_code == 200

    rows = (await client.get("/api/expenses", headers=auth_headers)).json()["data"]
    assert exp["id"] not in [r["id"] for r in rows]


# ── Monthly summary ──────────────────────────────────────────────────────────

async def test_monthly_summary_totals_current_month_by_category(
    client: AsyncClient, auth_headers: dict
):
    await _create_expense(client, auth_headers, category="fuel", amount=1000.0)
    await _create_expense(client, auth_headers, category="fuel", amount=500.0)
    await _create_expense(client, auth_headers, category="rent", amount=20000.0)

    resp = await client.get("/api/expenses/summary/monthly", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["by_category"]["fuel"] == 1500.0
    assert body["by_category"]["rent"] == 20000.0
    assert body["month_total"] == 21500.0


async def test_monthly_summary_excludes_other_months(client: AsyncClient, auth_headers: dict):
    # A date guaranteed to be outside the current month.
    last_month_end = TODAY.replace(day=1) - timedelta(days=1)
    await _create_expense(client, auth_headers, category="rent", amount=99999.0,
                          date=last_month_end.isoformat())

    body = (await client.get("/api/expenses/summary/monthly", headers=auth_headers)).json()
    assert body["month_total"] == 0.0


async def test_monthly_summary_is_zero_with_no_expenses(client: AsyncClient, auth_headers: dict):
    body = (await client.get("/api/expenses/summary/monthly", headers=auth_headers)).json()
    assert body["month_total"] == 0.0
    assert body["by_category"] == {}


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_expenses_are_scoped_to_the_org(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    await _create_expense(client, auth_headers, description="Confidential")
    rows = (await client.get("/api/expenses", headers=other_org_headers)).json()["data"]
    assert rows == []


async def test_another_org_cannot_delete_your_expense(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    exp = await _create_expense(client, auth_headers)
    resp = await client.delete(f"/api/expenses/{exp['id']}", headers=other_org_headers)
    assert resp.status_code == 404


async def test_another_orgs_expenses_do_not_leak_into_your_summary(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    await _create_expense(client, auth_headers, category="fuel", amount=5000.0)
    body = (await client.get("/api/expenses/summary/monthly", headers=other_org_headers)).json()
    assert body["month_total"] == 0.0
