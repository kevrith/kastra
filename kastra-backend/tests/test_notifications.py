"""In-app notifications: listing, unread counts, marking read."""
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


@pytest_asyncio.fixture
async def org_id(client: AsyncClient, auth_headers: dict) -> str:
    me = await client.get("/api/auth/me", headers=auth_headers)
    return me.json()["organization"]["id"]


async def _seed(db_session: AsyncSession, org_id: str, n: int = 1, **overrides):
    """Insert notifications directly — they're raised by services, not by an API."""
    created = []
    for i in range(n):
        note = Notification(
            organization_id=org_id,
            type=overrides.get("type", "payment_received"),
            title=overrides.get("title", f"Notification {i}"),
            body=overrides.get("body", "Something happened."),
            entity_id=overrides.get("entity_id"),
        )
        db_session.add(note)
        created.append(note)
    await db_session.commit()
    for note in created:
        await db_session.refresh(note)
    return created


# ── List ─────────────────────────────────────────────────────────────────────

async def test_list_notifications_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/notifications", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["unread_count"] == 0


async def test_list_notifications_counts_unread(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id, n=3)
    body = (await client.get("/api/notifications", headers=auth_headers)).json()
    assert len(body["items"]) == 3
    assert body["unread_count"] == 3


async def test_list_notifications_requires_auth(client: AsyncClient):
    resp = await client.get("/api/notifications")
    assert resp.status_code in (401, 403)


async def test_list_notifications_newest_first(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id, n=3)
    items = (await client.get("/api/notifications", headers=auth_headers)).json()["items"]
    timestamps = [i["created_at"] for i in items]
    assert timestamps == sorted(timestamps, reverse=True)


# ── Mark read ────────────────────────────────────────────────────────────────

async def test_mark_one_read(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    note = (await _seed(db_session, org_id))[0]
    resp = await client.patch(f"/api/notifications/{note.id}/read", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["read_at"] is not None

    body = (await client.get("/api/notifications", headers=auth_headers)).json()
    assert body["unread_count"] == 0


async def test_mark_read_is_idempotent(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    note = (await _seed(db_session, org_id))[0]
    first = await client.patch(f"/api/notifications/{note.id}/read", headers=auth_headers)
    second = await client.patch(f"/api/notifications/{note.id}/read", headers=auth_headers)
    assert second.status_code == 200
    assert second.json()["read_at"] == first.json()["read_at"]


async def test_mark_read_404s_for_unknown_id(client: AsyncClient, auth_headers: dict):
    resp = await client.patch(
        "/api/notifications/00000000-0000-0000-0000-000000000000/read", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_mark_all_read(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id, n=4)
    resp = await client.post("/api/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200

    body = (await client.get("/api/notifications", headers=auth_headers)).json()
    assert body["unread_count"] == 0
    assert all(i["read_at"] is not None for i in body["items"])


async def test_mark_all_read_with_nothing_unread(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 200


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_notifications_are_scoped_to_the_org(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict,
    db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id, n=2)
    body = (await client.get("/api/notifications", headers=other_org_headers)).json()
    assert body["items"] == []
    assert body["unread_count"] == 0


async def test_another_org_cannot_mark_your_notification_read(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict,
    db_session: AsyncSession, org_id: str
):
    note = (await _seed(db_session, org_id))[0]
    resp = await client.patch(f"/api/notifications/{note.id}/read", headers=other_org_headers)
    assert resp.status_code == 404


async def test_read_all_does_not_touch_another_orgs_notifications(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict,
    db_session: AsyncSession, org_id: str
):
    await _seed(db_session, org_id, n=2)
    await client.post("/api/notifications/read-all", headers=other_org_headers)

    body = (await client.get("/api/notifications", headers=auth_headers)).json()
    assert body["unread_count"] == 2
