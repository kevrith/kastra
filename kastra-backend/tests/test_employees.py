"""Employee register: CRUD, duplicate employee numbers, soft delete, role gating."""
from httpx import AsyncClient


async def _create_employee(client, headers, **overrides):
    payload = {
        "employee_no": "EMP-001",
        "full_name": "Grace Wanjiru",
        "job_title": "Site Supervisor",
        "basic_salary": "80000",
        "allowances": "10000",
        **overrides,
    }
    resp = await client.post("/api/employees", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# ── Create ───────────────────────────────────────────────────────────────────

async def test_create_employee(client: AsyncClient, auth_headers: dict):
    data = await _create_employee(client, auth_headers)
    assert data["employee_no"] == "EMP-001"
    assert data["full_name"] == "Grace Wanjiru"
    assert data["status"] == "active"
    assert data["employment_type"] == "permanent"


async def test_create_employee_requires_employee_no(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/employees", json={"full_name": "No Number"}, headers=auth_headers)
    assert resp.status_code == 422


async def test_duplicate_employee_no_is_rejected(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers, employee_no="EMP-DUP")
    resp = await client.post("/api/employees", json={
        "employee_no": "EMP-DUP", "full_name": "Someone Else",
    }, headers=auth_headers)
    assert resp.status_code == 409


async def test_same_employee_no_is_fine_in_a_different_org(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    await _create_employee(client, auth_headers, employee_no="EMP-SHARED")
    resp = await client.post("/api/employees", json={
        "employee_no": "EMP-SHARED", "full_name": "Other Org Staff",
    }, headers=other_org_headers)
    assert resp.status_code == 201


async def test_create_employee_requires_auth(client: AsyncClient):
    resp = await client.post("/api/employees", json={"employee_no": "X", "full_name": "Y"})
    assert resp.status_code in (401, 403)


# ── List / get ───────────────────────────────────────────────────────────────

async def test_list_employees_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/employees", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_employees_defaults_to_active_only(client: AsyncClient, auth_headers: dict):
    active = await _create_employee(client, auth_headers, employee_no="EMP-A", full_name="Active One")
    gone = await _create_employee(client, auth_headers, employee_no="EMP-B", full_name="Left Us")
    await client.delete(f"/api/employees/{gone['id']}", headers=auth_headers)

    ids = [e["id"] for e in (await client.get("/api/employees", headers=auth_headers)).json()]
    assert active["id"] in ids
    assert gone["id"] not in ids


async def test_list_employees_status_filter_finds_inactive(client: AsyncClient, auth_headers: dict):
    gone = await _create_employee(client, auth_headers, employee_no="EMP-C", full_name="Departed")
    await client.delete(f"/api/employees/{gone['id']}", headers=auth_headers)

    resp = await client.get("/api/employees?status=inactive", headers=auth_headers)
    assert resp.status_code == 200
    assert gone["id"] in [e["id"] for e in resp.json()]


async def test_list_employees_search_by_name_or_number(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers, employee_no="EMP-100", full_name="Peter Otieno")
    await _create_employee(client, auth_headers, employee_no="EMP-200", full_name="Mary Njeri")

    by_name = (await client.get("/api/employees?q=otieno", headers=auth_headers)).json()
    assert [e["full_name"] for e in by_name] == ["Peter Otieno"]

    by_no = (await client.get("/api/employees?q=EMP-200", headers=auth_headers)).json()
    assert [e["full_name"] for e in by_no] == ["Mary Njeri"]


async def test_get_employee(client: AsyncClient, auth_headers: dict):
    emp = await _create_employee(client, auth_headers)
    resp = await client.get(f"/api/employees/{emp['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == emp["id"]


async def test_get_unknown_employee_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/employees/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Update ───────────────────────────────────────────────────────────────────

async def test_update_employee_is_partial(client: AsyncClient, auth_headers: dict):
    emp = await _create_employee(client, auth_headers)
    resp = await client.put(f"/api/employees/{emp['id']}", json={
        "job_title": "Project Manager",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["job_title"] == "Project Manager"
    assert data["full_name"] == "Grace Wanjiru"  # untouched


async def test_update_to_a_taken_employee_no_is_rejected(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers, employee_no="EMP-X")
    other = await _create_employee(client, auth_headers, employee_no="EMP-Y", full_name="Other")

    resp = await client.put(f"/api/employees/{other['id']}", json={
        "employee_no": "EMP-X",
    }, headers=auth_headers)
    assert resp.status_code == 409


async def test_updating_an_employee_to_its_own_number_is_allowed(
    client: AsyncClient, auth_headers: dict
):
    emp = await _create_employee(client, auth_headers, employee_no="EMP-SELF")
    resp = await client.put(f"/api/employees/{emp['id']}", json={
        "employee_no": "EMP-SELF", "job_title": "Foreman",
    }, headers=auth_headers)
    assert resp.status_code == 200


async def test_update_unknown_employee_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.put("/api/employees/00000000-0000-0000-0000-000000000000", json={
        "job_title": "Ghost",
    }, headers=auth_headers)
    assert resp.status_code == 404


# ── Delete is a soft delete ──────────────────────────────────────────────────

async def test_delete_employee_marks_inactive_rather_than_erasing(
    client: AsyncClient, auth_headers: dict
):
    emp = await _create_employee(client, auth_headers)
    resp = await client.delete(f"/api/employees/{emp['id']}", headers=auth_headers)
    assert resp.status_code == 200

    # Still fetchable by id — payroll history must survive.
    fetched = await client.get(f"/api/employees/{emp['id']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["data"]["status"] == "inactive"


async def test_delete_unknown_employee_404s(client: AsyncClient, auth_headers: dict):
    resp = await client.delete(
        "/api/employees/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_employees_are_scoped_to_the_org(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    await _create_employee(client, auth_headers)
    assert (await client.get("/api/employees", headers=other_org_headers)).json() == []


async def test_another_org_cannot_read_your_employee(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    emp = await _create_employee(client, auth_headers)
    resp = await client.get(f"/api/employees/{emp['id']}", headers=other_org_headers)
    assert resp.status_code == 404


async def test_another_org_cannot_edit_your_employees_salary(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    emp = await _create_employee(client, auth_headers)
    resp = await client.put(f"/api/employees/{emp['id']}", json={
        "basic_salary": "1",
    }, headers=other_org_headers)
    assert resp.status_code == 404
