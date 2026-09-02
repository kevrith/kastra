"""Audit trail — write side.

test_audit_logs.py seeds rows directly and covers reading/filtering/export.
This file covers the half that matters for a security review: that ordinary
business actions actually leave a trace, and that a *failed* login does too.
"""
from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def _entries(db_session: AsyncSession, **where) -> list[AuditLog]:
    q = select(AuditLog).order_by(AuditLog.created_at.desc())
    for field, value in where.items():
        q = q.where(getattr(AuditLog, field) == value)
    return list((await db_session.execute(q)).scalars().all())


# ── Business actions leave a trace ───────────────────────────────────────────

async def test_creating_a_client_is_audited(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    resp = await client.post(
        "/api/clients", json={"name": "Audited Ltd"}, headers=auth_headers
    )
    assert resp.status_code == 201
    client_id = resp.json()["data"]["id"]

    rows = await _entries(db_session, resource_type="client", action="create")
    assert any(r.resource_id == client_id for r in rows)
    entry = next(r for r in rows if r.resource_id == client_id)
    assert "Audited Ltd" in entry.detail
    assert entry.user_id is not None      # who did it
    assert entry.organization_id is not None


async def test_updating_a_client_records_field_names_not_values(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    created = await client.post(
        "/api/clients", json={"name": "Before Ltd"}, headers=auth_headers
    )
    client_id = created.json()["data"]["id"]

    await client.put(
        f"/api/clients/{client_id}",
        json={"name": "Before Ltd", "phone": "254722000999"},
        headers=auth_headers,
    )

    rows = await _entries(db_session, resource_type="client", action="update")
    entry = next(r for r in rows if r.resource_id == client_id)
    assert "phone" in entry.detail
    # The number itself is PII and must not be copied into the log.
    assert "254722000999" not in entry.detail


async def test_deleting_a_client_is_audited(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    created = await client.post(
        "/api/clients", json={"name": "Doomed Ltd"}, headers=auth_headers
    )
    client_id = created.json()["data"]["id"]
    assert (await client.delete(
        f"/api/clients/{client_id}", headers=auth_headers
    )).status_code == 200

    rows = await _entries(db_session, resource_type="client", action="delete")
    assert any(r.resource_id == client_id for r in rows)


async def test_creating_an_expense_is_audited(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    resp = await client.post("/api/expenses", json={
        "category": "fuel", "description": "Site run",
        "amount": 2500, "date": "2026-01-15",
    }, headers=auth_headers)
    assert resp.status_code == 201

    rows = await _entries(db_session, resource_type="expense", action="create")
    assert any("Site run" in (r.detail or "") for r in rows)


# ── Auth events ──────────────────────────────────────────────────────────────

async def test_a_failed_login_is_audited_even_though_the_request_fails(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    """The request 401s and its session is rolled back, so this entry can only
    survive if it is written in an independent transaction."""
    me = await client.get("/api/auth/me", headers=auth_headers)
    email = me.json()["email"]

    resp = await client.post(
        "/api/auth/login", json={"email": email, "password": "not-the-password"}
    )
    assert resp.status_code == 401

    rows = await _entries(db_session, resource_type="auth", action="login_failed")
    assert rows, "a failed login must leave an audit entry"
    assert any("incorrect password" in (r.detail or "") for r in rows)


async def test_a_failed_login_for_an_unknown_email_is_audited_without_an_org(
    client: AsyncClient, db_session: AsyncSession
):
    resp = await client.post("/api/auth/login", json={
        "email": f"ghost-{datetime.now(timezone.utc).timestamp()}@example.com",
        "password": "whatever",
    })
    assert resp.status_code == 401

    rows = await _entries(db_session, resource_type="auth", action="login_failed")
    orphan = [r for r in rows if r.organization_id is None]
    assert orphan, "an attempt on a non-existent account is still recorded"
    # No tenant owns it, so no tenant should be able to read it.
    assert orphan[0].user_id is None


async def test_a_successful_login_is_audited(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    invite = await client.post("/api/team/invite", json={
        "email": f"loginaudit-{datetime.now(timezone.utc).timestamp()}@example.com",
        "role": "manager", "display_name": "Login Audit",
    }, headers=auth_headers)
    member = invite.json()
    await client.post("/api/team/accept-invite", json={
        "token": member["invite_token"], "password": "loginpass123",
    })

    resp = await client.post("/api/auth/login", json={
        "email": member["email"], "password": "loginpass123",
    })
    assert resp.status_code == 200

    rows = await _entries(db_session, resource_type="auth", action="login")
    assert rows, "a successful login must leave an audit entry"


async def test_inviting_a_team_member_is_audited(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    await client.post("/api/team/invite", json={
        "email": f"invited-{datetime.now(timezone.utc).timestamp()}@example.com",
        "role": "viewer", "display_name": "Invited",
    }, headers=auth_headers)

    rows = await _entries(db_session, resource_type="organization", action="create")
    assert any("viewer" in (r.detail or "") for r in rows)
