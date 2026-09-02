"""Projects: creation from an accepted quotation, stage moves, updates, financials."""
import pytest_asyncio
from datetime import date
from httpx import AsyncClient

_ITEMS = [{"description": "Site works", "quantity": "1", "unit_price": "200000.00"}]


async def _accepted_quotation(client, headers, client_id) -> str:
    qt = await client.post("/api/quotations", json={
        "client_id": client_id, "items": _ITEMS,
    }, headers=headers)
    qt_id = qt.json()["data"]["id"]
    await client.patch(f"/api/quotations/{qt_id}/status", json={"status": "accepted"}, headers=headers)
    return qt_id


@pytest_asyncio.fixture
async def project(client: AsyncClient, auth_headers: dict, sample_client_id: str) -> dict:
    qt_id = await _accepted_quotation(client, auth_headers, sample_client_id)
    resp = await client.post("/api/projects", json={
        "quotation_id": qt_id, "title": "Westlands office fit-out",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Create ───────────────────────────────────────────────────────────────────

async def test_create_project_from_an_accepted_quotation(project: dict):
    assert project["title"] == "Westlands office fit-out"
    assert project["stage"] == "not_started"
    assert project["completed_at"] is None
    assert project["updates"] == []
    assert project["photos"] == []


async def test_project_inherits_the_quotations_client(
    project: dict, sample_client_id: str
):
    assert project["client_id"] == sample_client_id


async def test_cannot_create_a_project_from_a_draft_quotation(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    qt = await client.post("/api/quotations", json={
        "client_id": sample_client_id, "items": _ITEMS,
    }, headers=auth_headers)
    resp = await client.post("/api/projects", json={
        "quotation_id": qt.json()["data"]["id"], "title": "Too early",
    }, headers=auth_headers)
    assert resp.status_code == 400


async def test_cannot_create_two_projects_from_one_quotation(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    qt_id = await _accepted_quotation(client, auth_headers, sample_client_id)
    first = await client.post("/api/projects", json={"quotation_id": qt_id, "title": "A"},
                              headers=auth_headers)
    assert first.status_code == 201
    second = await client.post("/api/projects", json={"quotation_id": qt_id, "title": "B"},
                               headers=auth_headers)
    assert second.status_code == 409


async def test_create_project_404s_for_an_unknown_quotation(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.post("/api/projects", json={
        "quotation_id": "QT-DOES-NOT-EXIST", "title": "Ghost",
    }, headers=auth_headers)
    assert resp.status_code == 404


async def test_create_project_requires_auth(client: AsyncClient):
    resp = await client.post("/api/projects", json={"quotation_id": "QT-1", "title": "X"})
    assert resp.status_code in (401, 403)


# ── List / get ───────────────────────────────────────────────────────────────

async def test_list_projects_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/projects", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_projects_contains_the_new_project(
    client: AsyncClient, auth_headers: dict, project: dict
):
    ids = [p["id"] for p in (await client.get("/api/projects", headers=auth_headers)).json()]
    assert project["id"] in ids


async def test_list_projects_filter_by_stage(
    client: AsyncClient, auth_headers: dict, project: dict
):
    await client.patch(f"/api/projects/{project['id']}", json={"stage": "in_progress"},
                       headers=auth_headers)

    in_progress = (await client.get("/api/projects?stage=in_progress", headers=auth_headers)).json()
    assert [p["id"] for p in in_progress] == [project["id"]]

    not_started = (await client.get("/api/projects?stage=not_started", headers=auth_headers)).json()
    assert not_started == []


async def test_get_project_detail(client: AsyncClient, auth_headers: dict, project: dict):
    resp = await client.get(f"/api/projects/{project['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == project["id"]


async def test_get_unknown_project_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/projects/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Stage transitions ────────────────────────────────────────────────────────

async def test_patch_stage_returns_200_with_the_full_project(
    client: AsyncClient, auth_headers: dict, project: dict
):
    """Regression: PATCH used to 500 — ProjectOut lazy-loaded updates/photos."""
    resp = await client.patch(f"/api/projects/{project['id']}", json={"stage": "in_progress"},
                              headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stage"] == "in_progress"
    assert body["updates"] == []
    assert body["photos"] == []


async def test_every_valid_stage_is_accepted(
    client: AsyncClient, auth_headers: dict, project: dict
):
    for stage in ("not_started", "in_progress", "on_hold", "completed", "invoiced"):
        resp = await client.patch(f"/api/projects/{project['id']}", json={"stage": stage},
                                  headers=auth_headers)
        assert resp.status_code == 200, f"{stage}: {resp.text}"
        assert resp.json()["stage"] == stage


async def test_an_unknown_stage_is_rejected(
    client: AsyncClient, auth_headers: dict, project: dict
):
    resp = await client.patch(f"/api/projects/{project['id']}", json={"stage": "teleporting"},
                              headers=auth_headers)
    assert resp.status_code == 422


async def test_completing_a_project_stamps_completed_at(
    client: AsyncClient, auth_headers: dict, project: dict
):
    resp = await client.patch(f"/api/projects/{project['id']}", json={"stage": "completed"},
                              headers=auth_headers)
    assert resp.json()["completed_at"] is not None


async def test_completed_at_is_not_overwritten_on_a_later_move(
    client: AsyncClient, auth_headers: dict, project: dict
):
    first = await client.patch(f"/api/projects/{project['id']}", json={"stage": "completed"},
                               headers=auth_headers)
    stamped = first.json()["completed_at"]

    await client.patch(f"/api/projects/{project['id']}", json={"stage": "on_hold"},
                       headers=auth_headers)
    again = await client.patch(f"/api/projects/{project['id']}", json={"stage": "completed"},
                               headers=auth_headers)
    assert again.json()["completed_at"] == stamped


async def test_patch_can_edit_title_and_description(
    client: AsyncClient, auth_headers: dict, project: dict
):
    resp = await client.patch(f"/api/projects/{project['id']}", json={
        "title": "Westlands fit-out (rev B)", "description": "Scope expanded to level 3.",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Westlands fit-out (rev B)"
    assert resp.json()["description"] == "Scope expanded to level 3."


async def test_patch_unknown_project_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.patch("/api/projects/00000000-0000-0000-0000-000000000000",
                              json={"stage": "completed"}, headers=auth_headers)
    assert resp.status_code == 404


# ── Progress updates ─────────────────────────────────────────────────────────

async def test_post_a_progress_update(client: AsyncClient, auth_headers: dict, project: dict):
    resp = await client.post(f"/api/projects/{project['id']}/updates", json={
        "body": "Foundation poured, curing until Friday.",
    }, headers=auth_headers)
    assert resp.status_code == 201

    detail = (await client.get(f"/api/projects/{project['id']}", headers=auth_headers)).json()
    assert len(detail["updates"]) == 1
    assert detail["updates"][0]["body"] == "Foundation poured, curing until Friday."


async def test_updates_surface_in_the_list_view(
    client: AsyncClient, auth_headers: dict, project: dict
):
    await client.post(f"/api/projects/{project['id']}/updates", json={"body": "Day 1"},
                      headers=auth_headers)
    row = [p for p in (await client.get("/api/projects", headers=auth_headers)).json()
           if p["id"] == project["id"]][0]
    assert row["last_update_at"] is not None


async def test_update_on_unknown_project_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/projects/00000000-0000-0000-0000-000000000000/updates",
                             json={"body": "hello"}, headers=auth_headers)
    assert resp.status_code == 404


# ── Financials ───────────────────────────────────────────────────────────────

async def test_financials_start_at_full_margin(
    client: AsyncClient, auth_headers: dict, project: dict
):
    resp = await client.get(f"/api/projects/{project['id']}/financials", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["revenue"] > 0
    assert body["expenses"] == 0.0
    assert body["profit"] == body["revenue"]
    assert body["margin"] == 100.0


async def test_project_expenses_reduce_the_margin(
    client: AsyncClient, auth_headers: dict, project: dict
):
    before = (await client.get(f"/api/projects/{project['id']}/financials",
                               headers=auth_headers)).json()
    await client.post("/api/expenses", json={
        "category": "materials", "description": "Cement", "amount": 50000.0,
        "date": date.today().isoformat(), "project_id": project["id"],
    }, headers=auth_headers)

    after = (await client.get(f"/api/projects/{project['id']}/financials",
                              headers=auth_headers)).json()
    assert after["expenses"] == 50000.0
    assert after["profit"] == before["revenue"] - 50000.0
    assert after["margin"] < before["margin"]


async def test_financials_404_for_unknown_project(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/projects/00000000-0000-0000-0000-000000000000/financials",
                            headers=auth_headers)
    assert resp.status_code == 404


# ── Delete ───────────────────────────────────────────────────────────────────

async def test_delete_project(client: AsyncClient, auth_headers: dict, project: dict):
    resp = await client.delete(f"/api/projects/{project['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert (await client.get("/api/projects", headers=auth_headers)).json() == []


async def test_delete_unknown_project_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.delete("/api/projects/00000000-0000-0000-0000-000000000000",
                               headers=auth_headers)
    assert resp.status_code == 404


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_projects_are_scoped_to_the_org(
    client: AsyncClient, other_org_headers: dict, project: dict
):
    assert (await client.get("/api/projects", headers=other_org_headers)).json() == []


async def test_another_org_cannot_read_your_project(
    client: AsyncClient, other_org_headers: dict, project: dict
):
    resp = await client.get(f"/api/projects/{project['id']}", headers=other_org_headers)
    assert resp.status_code == 403


async def test_another_org_cannot_move_your_project(
    client: AsyncClient, other_org_headers: dict, project: dict
):
    resp = await client.patch(f"/api/projects/{project['id']}", json={"stage": "completed"},
                              headers=other_org_headers)
    assert resp.status_code == 404


async def test_another_org_cannot_see_your_project_financials(
    client: AsyncClient, other_org_headers: dict, project: dict
):
    resp = await client.get(f"/api/projects/{project['id']}/financials", headers=other_org_headers)
    assert resp.status_code == 404
