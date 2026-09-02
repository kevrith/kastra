"""Team management: invites, activation, permission overrides, admin-only gating."""
import uuid

import pytest_asyncio
from httpx import AsyncClient

_ALL_PERMS = {
    "can_view_invoices", "can_create_invoices", "can_edit_invoices", "can_delete_invoices",
    "can_view_quotations", "can_create_quotations", "can_edit_quotations", "can_delete_quotations",
    "can_view_clients", "can_create_clients", "can_edit_clients", "can_delete_clients",
    "can_view_reports", "can_view_expenses", "can_create_expenses",
    "can_view_projects", "can_manage_projects",
}


def _unique_email(prefix: str = "invitee") -> str:
    """Test rows persist across the module, so every invite needs a fresh address."""
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


async def _invite(client, headers, email=None, role="manager", name="New Hire"):
    resp = await client.post("/api/team/invite", json={
        "email": email or _unique_email(), "role": role, "display_name": name,
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def invited_member(client: AsyncClient, auth_headers: dict) -> dict:
    return await _invite(client, auth_headers)


# ── Listing ──────────────────────────────────────────────────────────────────

async def test_list_team_shows_the_founder(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/team", headers=auth_headers)
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["role"] == "admin"
    assert members[0]["is_active"] is True


async def test_list_team_requires_auth(client: AsyncClient):
    resp = await client.get("/api/team")
    assert resp.status_code in (401, 403)


# ── Invites ──────────────────────────────────────────────────────────────────

async def test_invite_returns_a_shareable_link(invited_member: dict):
    assert invited_member["email"].endswith("@example.com")
    assert invited_member["role"] == "manager"
    assert invited_member["is_active"] is False
    assert invited_member["invite_token"]
    assert invited_member["invite_token"] in invited_member["invite_link"]


async def test_invited_member_appears_in_the_team_list(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    members = (await client.get("/api/team", headers=auth_headers)).json()
    assert invited_member["id"] in [m["id"] for m in members]


async def test_invite_rejects_an_unknown_role(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/team/invite", json={
        "email": "x@example.com", "role": "superuser", "display_name": "X",
    }, headers=auth_headers)
    assert resp.status_code == 422


async def test_invite_accepts_each_valid_role(client: AsyncClient, auth_headers: dict):
    for role in ("admin", "manager", "field_agent", "viewer"):
        member = await _invite(client, auth_headers, role=role)
        assert member["role"] == role


async def test_inviting_an_existing_member_twice_is_rejected(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    resp = await client.post("/api/team/invite", json={
        "email": invited_member["email"], "role": "viewer", "display_name": "Dup",
    }, headers=auth_headers)
    assert resp.status_code == 409


async def test_inviting_someone_from_another_org_is_rejected(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    other_me = await client.get("/api/auth/me", headers=other_org_headers)
    resp = await client.post("/api/team/invite", json={
        "email": other_me.json()["email"], "role": "viewer", "display_name": "Poach",
    }, headers=auth_headers)
    assert resp.status_code == 409


# ── Accepting an invite ──────────────────────────────────────────────────────

async def test_accepting_an_invite_activates_the_account(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    resp = await client.post("/api/team/accept-invite", json={
        "token": invited_member["invite_token"], "password": "newhirepass123",
    })
    assert resp.status_code == 200

    login = await client.post("/api/auth/login", json={
        "email": invited_member["email"], "password": "newhirepass123",
    })
    assert login.status_code == 200, login.text
    assert "access_token" in login.json()


async def test_accepting_an_invite_rejects_a_short_password(
    client: AsyncClient, invited_member: dict
):
    resp = await client.post("/api/team/accept-invite", json={
        "token": invited_member["invite_token"], "password": "short",
    })
    assert resp.status_code == 422


async def test_accepting_an_invite_rejects_a_bogus_token(client: AsyncClient):
    resp = await client.post("/api/team/accept-invite", json={
        "token": "not-a-real-token", "password": "longenoughpass",
    })
    assert resp.status_code == 400


async def test_an_invite_token_cannot_be_reused(
    client: AsyncClient, invited_member: dict
):
    token = invited_member["invite_token"]
    first = await client.post("/api/team/accept-invite", json={
        "token": token, "password": "newhirepass123",
    })
    assert first.status_code == 200

    second = await client.post("/api/team/accept-invite", json={
        "token": token, "password": "differentpass123",
    })
    assert second.status_code == 400


# ── Member updates ───────────────────────────────────────────────────────────

async def test_deactivating_a_member(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    resp = await client.patch(f"/api/team/{invited_member['id']}", json={"is_active": False},
                              headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_deactivating_a_member_ends_their_session(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    await client.post("/api/team/accept-invite", json={
        "token": invited_member["invite_token"], "password": "newhirepass123",
    })
    login = await client.post("/api/auth/login", json={
        "email": invited_member["email"], "password": "newhirepass123",
    })
    member_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.get("/api/auth/me", headers=member_headers)).status_code == 200

    await client.patch(f"/api/team/{invited_member['id']}", json={"is_active": False},
                       headers=auth_headers)
    assert (await client.get("/api/auth/me", headers=member_headers)).status_code == 401


async def test_role_changes_are_refused(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    resp = await client.patch(f"/api/team/{invited_member['id']}", json={"role": "admin"},
                              headers=auth_headers)
    assert resp.status_code == 403


async def test_you_cannot_modify_yourself(client: AsyncClient, auth_headers: dict):
    me = await client.get("/api/auth/me", headers=auth_headers)
    resp = await client.patch(f"/api/team/{me.json()['id']}", json={"is_active": False},
                              headers=auth_headers)
    assert resp.status_code == 400


async def test_you_cannot_remove_yourself(client: AsyncClient, auth_headers: dict):
    me = await client.get("/api/auth/me", headers=auth_headers)
    resp = await client.delete(f"/api/team/{me.json()['id']}", headers=auth_headers)
    assert resp.status_code == 400


async def test_remove_a_team_member(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    resp = await client.delete(f"/api/team/{invited_member['id']}", headers=auth_headers)
    assert resp.status_code == 200

    members = (await client.get("/api/team", headers=auth_headers)).json()
    assert invited_member["id"] not in [m["id"] for m in members]


async def test_reset_a_members_password(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    await client.post("/api/team/accept-invite", json={
        "token": invited_member["invite_token"], "password": "newhirepass123",
    })
    resp = await client.post(f"/api/team/{invited_member['id']}/reset-password",
                             headers=auth_headers)
    assert resp.status_code == 200


# ── Permission overrides ─────────────────────────────────────────────────────

async def test_permissions_default_to_all_false(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    resp = await client.get(f"/api/team/{invited_member['id']}/permissions", headers=auth_headers)
    assert resp.status_code == 200
    perms = resp.json()
    assert set(perms) == _ALL_PERMS
    assert not any(perms.values())


async def test_set_and_read_back_permissions(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    payload = {p: False for p in _ALL_PERMS}
    payload["can_view_invoices"] = True
    payload["can_view_reports"] = True

    resp = await client.put(f"/api/team/{invited_member['id']}/permissions", json=payload,
                            headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["can_view_invoices"] is True

    read_back = await client.get(f"/api/team/{invited_member['id']}/permissions",
                                 headers=auth_headers)
    assert read_back.json()["can_view_reports"] is True
    assert read_back.json()["can_delete_invoices"] is False


async def test_permissions_can_be_revoked(
    client: AsyncClient, auth_headers: dict, invited_member: dict
):
    granted = {p: False for p in _ALL_PERMS} | {"can_view_expenses": True}
    await client.put(f"/api/team/{invited_member['id']}/permissions", json=granted,
                     headers=auth_headers)

    revoked = {p: False for p in _ALL_PERMS}
    resp = await client.put(f"/api/team/{invited_member['id']}/permissions", json=revoked,
                            headers=auth_headers)
    assert resp.json()["can_view_expenses"] is False


async def test_admins_cannot_be_given_overrides(client: AsyncClient, auth_headers: dict):
    me = await client.get("/api/auth/me", headers=auth_headers)
    resp = await client.put(f"/api/team/{me.json()['id']}/permissions",
                            json={p: True for p in _ALL_PERMS}, headers=auth_headers)
    assert resp.status_code == 400


async def test_a_granted_permission_actually_opens_the_endpoint(
    client: AsyncClient, auth_headers: dict
):
    """A viewer has no expense rights by default; an override should grant them."""
    member = await _invite(client, auth_headers, role="viewer", name="Viewer")
    await client.post("/api/team/accept-invite", json={
        "token": member["invite_token"], "password": "viewerpass123",
    })
    login = await client.post("/api/auth/login", json={
        "email": member["email"], "password": "viewerpass123",
    })
    viewer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    blocked = await client.get("/api/expenses", headers=viewer_headers)
    assert blocked.status_code == 403

    await client.put(f"/api/team/{member['id']}/permissions",
                     json={p: False for p in _ALL_PERMS} | {"can_view_expenses": True},
                     headers=auth_headers)

    allowed = await client.get("/api/expenses", headers=viewer_headers)
    assert allowed.status_code == 200


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_team_lists_are_scoped_to_the_org(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict, invited_member: dict
):
    members = (await client.get("/api/team", headers=other_org_headers)).json()
    assert invited_member["id"] not in [m["id"] for m in members]


async def test_another_org_cannot_deactivate_your_member(
    client: AsyncClient, other_org_headers: dict, invited_member: dict
):
    resp = await client.patch(f"/api/team/{invited_member['id']}", json={"is_active": False},
                              headers=other_org_headers)
    assert resp.status_code == 404


async def test_another_org_cannot_read_your_members_permissions(
    client: AsyncClient, other_org_headers: dict, invited_member: dict
):
    resp = await client.get(f"/api/team/{invited_member['id']}/permissions",
                            headers=other_org_headers)
    assert resp.status_code == 404
