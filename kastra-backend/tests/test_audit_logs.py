"""Audit trail: admin-only listing, filters, CSV export, org isolation.

These tests seed rows directly and exercise the read side; the write side lives
in test_audit_trail.py. Business actions are audited too, and the fixtures here
sign a user in, so every org starts with a real `login` entry — assertions that
care about counts scope themselves to the seeded action rather than the whole log.
"""
from datetime import datetime, timedelta, timezone

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


@pytest_asyncio.fixture
async def org_id(client: AsyncClient, auth_headers: dict) -> str:
    me = await client.get("/api/auth/me", headers=auth_headers)
    return me.json()["organization"]["id"]


async def _seed(db_session: AsyncSession, org_id: str, **overrides) -> AuditLog:
    entry = AuditLog(
        organization_id=str(org_id),
        user_id=overrides.get("user_id"),
        action=overrides.get("action", "mpesa_payment"),
        resource_type=overrides.get("resource_type", "invoice"),
        resource_id=overrides.get("resource_id", "INV-0001"),
        detail=overrides.get("detail", "KSh 50,000.00 received"),
        ip_address=overrides.get("ip_address", "196.201.0.1"),
    )
    if "created_at" in overrides:
        entry.created_at = overrides["created_at"]
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)
    return entry


# ── Access control ───────────────────────────────────────────────────────────

async def test_audit_log_requires_auth(client: AsyncClient):
    resp = await client.get("/api/audit-logs")
    assert resp.status_code in (401, 403)


async def test_a_non_admin_cannot_read_the_audit_log(
    client: AsyncClient, auth_headers: dict
):
    invite = await client.post("/api/team/invite", json={
        "email": f"auditor-{datetime.now(timezone.utc).timestamp()}@example.com",
        "role": "manager", "display_name": "Manager",
    }, headers=auth_headers)
    member = invite.json()
    await client.post("/api/team/accept-invite", json={
        "token": member["invite_token"], "password": "managerpass123",
    })
    login = await client.post("/api/auth/login", json={
        "email": member["email"], "password": "managerpass123",
    })
    manager_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get("/api/audit-logs", headers=manager_headers)
    assert resp.status_code == 403


# ── Listing ──────────────────────────────────────────────────────────────────

async def test_a_new_org_has_no_business_activity_logged(
    client: AsyncClient, auth_headers: dict
):
    """Signing in is itself audited, so scope to the business entries."""
    resp = await client.get("/api/audit-logs?resource_type=invoice", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["meta"]["total"] == 0


async def test_seeded_entry_is_listed(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id)
    body = (await client.get("/api/audit-logs?action=mpesa_payment",
                             headers=auth_headers)).json()
    assert body["meta"]["total"] == 1
    entry = body["data"][0]
    assert entry["action"] == "mpesa_payment"
    assert entry["resource_id"] == "INV-0001"
    assert entry["ip_address"] == "196.201.0.1"


async def test_entries_are_newest_first(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    now = datetime.now(timezone.utc)
    await _seed(db_session, org_id, resource_id="OLD", created_at=now - timedelta(days=2))
    await _seed(db_session, org_id, resource_id="NEW", created_at=now)

    rows = (await client.get("/api/audit-logs?action=mpesa_payment",
                             headers=auth_headers)).json()["data"]
    assert [r["resource_id"] for r in rows] == ["NEW", "OLD"]


async def test_filter_by_action(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id, action="mpesa_payment")
    await _seed(db_session, org_id, action="paystack_payment")

    body = (await client.get("/api/audit-logs?action=paystack_payment",
                             headers=auth_headers)).json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["action"] == "paystack_payment"


async def test_filter_by_resource_type(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id, resource_type="invoice")
    await _seed(db_session, org_id, resource_type="subscription")

    body = (await client.get("/api/audit-logs?resource_type=subscription",
                             headers=auth_headers)).json()
    assert [r["resource_type"] for r in body["data"]] == ["subscription"]


async def test_filter_from_date(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    """The UI sends plain YYYY-MM-DD — an untyped filter here used to 500."""
    now = datetime.now(timezone.utc)
    await _seed(db_session, org_id, resource_id="ANCIENT", created_at=now - timedelta(days=60))
    await _seed(db_session, org_id, resource_id="RECENT", created_at=now)

    cutoff = (now - timedelta(days=7)).date().isoformat()
    resp = await client.get(f"/api/audit-logs?from_date={cutoff}&action=mpesa_payment", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert [r["resource_id"] for r in resp.json()["data"]] == ["RECENT"]


async def test_filter_to_date_includes_the_whole_day(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    """A date picker's `to_date` means 'through the end of that day'."""
    now = datetime.now(timezone.utc)
    await _seed(db_session, org_id, resource_id="TODAY", created_at=now)

    resp = await client.get(f"/api/audit-logs?to_date={now.date().isoformat()}&action=mpesa_payment",
                            headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert [r["resource_id"] for r in resp.json()["data"]] == ["TODAY"]


async def test_filter_to_date_excludes_later_entries(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    now = datetime.now(timezone.utc)
    await _seed(db_session, org_id, resource_id="LATER", created_at=now + timedelta(days=3))

    resp = await client.get(f"/api/audit-logs?to_date={now.date().isoformat()}&action=mpesa_payment",
                            headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == []


async def test_filter_by_both_bounds(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    now = datetime.now(timezone.utc)
    await _seed(db_session, org_id, resource_id="BEFORE", created_at=now - timedelta(days=30))
    await _seed(db_session, org_id, resource_id="INSIDE", created_at=now - timedelta(days=5))
    await _seed(db_session, org_id, resource_id="AFTER", created_at=now + timedelta(days=30))

    start = (now - timedelta(days=10)).date().isoformat()
    end = now.date().isoformat()
    resp = await client.get(f"/api/audit-logs?from_date={start}&to_date={end}&action=mpesa_payment",
                            headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert [r["resource_id"] for r in resp.json()["data"]] == ["INSIDE"]


async def test_a_malformed_date_is_a_422_not_a_500(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/audit-logs?from_date=last-tuesday", headers=auth_headers)
    assert resp.status_code == 422


async def test_pagination(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    for i in range(5):
        await _seed(db_session, org_id, resource_id=f"INV-{i}")

    body = (await client.get("/api/audit-logs?limit=2&action=mpesa_payment",
                             headers=auth_headers)).json()
    assert len(body["data"]) == 2
    assert body["meta"]["total"] == 5
    assert body["meta"]["pages"] == 3


async def test_limit_is_capped(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/audit-logs?limit=1000", headers=auth_headers)
    assert resp.status_code == 422


# ── CSV export ───────────────────────────────────────────────────────────────

async def test_csv_export_headers(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/audit-logs/export/csv", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "kastra-audit-log.csv" in resp.headers["content-disposition"]
    assert resp.text.splitlines()[0].startswith("Timestamp,Action,Resource Type")


async def test_csv_export_includes_entries(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id, resource_id="INV-CSV")
    resp = await client.get("/api/audit-logs/export/csv", headers=auth_headers)
    assert "INV-CSV" in resp.text
    assert "mpesa_payment" in resp.text


async def test_csv_export_honours_the_date_range(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    now = datetime.now(timezone.utc)
    await _seed(db_session, org_id, resource_id="OLD-ROW", created_at=now - timedelta(days=60))
    await _seed(db_session, org_id, resource_id="NEW-ROW", created_at=now)

    cutoff = (now - timedelta(days=7)).date().isoformat()
    resp = await client.get(f"/api/audit-logs/export/csv?from_date={cutoff}",
                            headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert "NEW-ROW" in resp.text
    assert "OLD-ROW" not in resp.text


async def test_csv_export_requires_admin(client: AsyncClient):
    resp = await client.get("/api/audit-logs/export/csv")
    assert resp.status_code in (401, 403)


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_audit_entries_are_scoped_to_the_org(
    client: AsyncClient, other_org_headers: dict, db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id, resource_id="SECRET")
    body = (await client.get("/api/audit-logs", headers=other_org_headers)).json()
    # The other org sees its own sign-in, but must never see org A's rows.
    assert "SECRET" not in [r["resource_id"] for r in body["data"]]
    assert all(r["action"] != "mpesa_payment" for r in body["data"])


async def test_csv_export_never_leaks_another_org(
    client: AsyncClient, other_org_headers: dict, db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id, resource_id="SECRET")
    resp = await client.get("/api/audit-logs/export/csv", headers=other_org_headers)
    assert "SECRET" not in resp.text
