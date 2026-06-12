from decimal import Decimal

from httpx import AsyncClient

from app.services import payroll_service

# ---------------------------------------------------------------------------
# payroll_service.compute_payslip — pure statutory-calculation unit tests.
#
# These pin down the Kenyan PAYE/NSSF/SHIF/Housing-Levy maths against
# hand-computed expected values (cross-checked with public payroll
# calculators) so a future change to bands/rates/rounding can't silently
# drift without a test failing.
# ---------------------------------------------------------------------------

def test_compute_payslip_low_earner_paye_zeroed_by_relief():
    """At KES 5,000 basic: SHIF hits its minimum and personal relief fully
    absorbs the (small) PAYE liability, so PAYE should be zero, not negative."""
    result = payroll_service.compute_payslip(basic_salary=Decimal("5000"))

    assert result.gross_pay == Decimal("5000.00")
    assert result.nssf == Decimal("300.00")           # 6% of 5,000 (below LEL, tier I only)
    assert result.shif == Decimal("300.00")           # 2.75% of 5,000 = 137.50 -> minimum applies
    assert result.housing_levy == Decimal("75.00")    # 1.5% of 5,000
    assert result.taxable_income == Decimal("4325.00")
    assert result.paye == Decimal("0.00")             # 432.50 tax - 2,400 relief -> floored at 0
    assert result.personal_relief == Decimal("2400.00")
    assert result.total_deductions == Decimal("675.00")
    assert result.net_pay == Decimal("4325.00")


def test_compute_payslip_mid_earner_30k():
    """KES 30,000 basic — crosses into the second PAYE band; NSSF spans
    both tier I (up to LEL) and tier II (LEL..gross)."""
    result = payroll_service.compute_payslip(basic_salary=Decimal("30000"))

    assert result.gross_pay == Decimal("30000.00")
    assert result.nssf == Decimal("1800.00")          # 480 (tier I) + 1,320 (tier II)
    assert result.shif == Decimal("825.00")           # 2.75% of 30,000
    assert result.housing_levy == Decimal("450.00")   # 1.5% of 30,000
    assert result.taxable_income == Decimal("26925.00")
    assert result.paye == Decimal("731.25")           # (3,131.25 before relief) - 2,400
    assert result.total_deductions == Decimal("3806.25")
    assert result.net_pay == Decimal("26193.75")


def test_compute_payslip_high_earner_80k_nssf_capped():
    """KES 80,000 basic — gross exceeds the NSSF upper earnings limit, so
    pensionable pay is capped at 72,000 (max employee NSSF = KES 4,320)."""
    result = payroll_service.compute_payslip(basic_salary=Decimal("80000"))

    assert result.gross_pay == Decimal("80000.00")
    assert result.nssf == Decimal("4320.00")          # capped: 480 + (64,000 * 6%)
    assert result.shif == Decimal("2200.00")
    assert result.housing_levy == Decimal("1200.00")
    assert result.taxable_income == Decimal("72280.00")
    assert result.paye == Decimal("14067.35")
    assert result.total_deductions == Decimal("21787.35")
    assert result.net_pay == Decimal("58212.65")


def test_compute_payslip_very_high_earner_250k_third_band():
    """KES 250,000 basic — taxable income lands in the 30% PAYE band."""
    result = payroll_service.compute_payslip(basic_salary=Decimal("250000"))

    assert result.gross_pay == Decimal("250000.00")
    assert result.nssf == Decimal("4320.00")          # still capped at the UEL
    assert result.shif == Decimal("6875.00")
    assert result.housing_levy == Decimal("3750.00")
    assert result.taxable_income == Decimal("235055.00")
    assert result.paye == Decimal("62899.85")
    assert result.total_deductions == Decimal("77844.85")
    assert result.net_pay == Decimal("172155.15")


def test_compute_payslip_includes_allowances_in_gross():
    """Allowances must be added to basic salary before any statutory
    calculation runs — getting the order wrong would underpay every deduction."""
    with_allowance = payroll_service.compute_payslip(basic_salary=Decimal("50000"), allowances=Decimal("5000"))
    without_allowance = payroll_service.compute_payslip(basic_salary=Decimal("50000"))

    assert with_allowance.gross_pay == Decimal("55000.00")
    assert with_allowance.gross_pay != without_allowance.gross_pay
    # NSSF/SHIF/Housing Levy/PAYE are all derived from gross — they must differ too
    assert with_allowance.total_deductions > without_allowance.total_deductions
    assert with_allowance.net_pay == with_allowance.gross_pay - with_allowance.total_deductions


def test_compute_payslip_other_deductions_reduce_net_pay():
    base = payroll_service.compute_payslip(basic_salary=Decimal("40000"))
    with_loan = payroll_service.compute_payslip(basic_salary=Decimal("40000"), other_deductions=Decimal("2000"))

    assert with_loan.other_deductions == Decimal("2000.00")
    assert with_loan.total_deductions == base.total_deductions + Decimal("2000.00")
    assert with_loan.net_pay == base.net_pay - Decimal("2000.00")


def test_compute_payslip_net_pay_reconciles_to_gross_minus_deductions():
    """Sanity invariant that must hold for every payslip regardless of salary band."""
    for basic in ("12000", "45000", "120000", "600000"):
        result = payroll_service.compute_payslip(basic_salary=Decimal(basic))
        assert result.net_pay == result.gross_pay - result.total_deductions
        assert result.total_deductions == (
            result.nssf + result.shif + result.housing_levy + result.paye + result.other_deductions
        )
        assert result.paye >= Decimal("0")
        assert result.net_pay >= Decimal("0")


# ---------------------------------------------------------------------------
# Helpers for the API-level tests below
# ---------------------------------------------------------------------------

_counter = {"n": 0}


async def _create_employee(client, auth_headers, basic_salary="50000", allowances="0", **overrides):
    _counter["n"] += 1
    payload = {
        "employee_no": f"EMP-{_counter['n']:04d}",
        "full_name": f"Test Employee {_counter['n']}",
        "basic_salary": basic_salary,
        "allowances": allowances,
        **overrides,
    }
    resp = await client.post("/api/employees", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def _create_run(client, auth_headers, year=2026, month=1, notes=None):
    payload = {"period_year": year, "period_month": month}
    if notes:
        payload["notes"] = notes
    resp = await client.post("/api/payroll/runs", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# Employees — CRUD
# ---------------------------------------------------------------------------

async def test_create_employee_returns_201(client: AsyncClient, auth_headers: dict):
    emp = await _create_employee(client, auth_headers, basic_salary="45000.00", allowances="5000.00")
    assert emp["status"] == "active"
    assert Decimal(emp["basic_salary"]) == Decimal("45000.00")
    assert Decimal(emp["allowances"]) == Decimal("5000.00")


async def test_create_employee_duplicate_employee_no_rejected(client: AsyncClient, auth_headers: dict):
    await client.post("/api/employees", json={
        "employee_no": "DUP-001", "full_name": "First Person",
    }, headers=auth_headers)
    resp = await client.post("/api/employees", json={
        "employee_no": "DUP-001", "full_name": "Second Person",
    }, headers=auth_headers)
    assert resp.status_code == 409


async def test_list_employees_excludes_inactive_by_default(client: AsyncClient, auth_headers: dict):
    emp = await _create_employee(client, auth_headers)
    await client.delete(f"/api/employees/{emp['id']}", headers=auth_headers)

    active_resp = await client.get("/api/employees", headers=auth_headers)
    assert all(e["id"] != emp["id"] for e in active_resp.json())

    inactive_resp = await client.get("/api/employees?status=inactive", headers=auth_headers)
    assert any(e["id"] == emp["id"] for e in inactive_resp.json())


async def test_get_employee(client: AsyncClient, auth_headers: dict):
    emp = await _create_employee(client, auth_headers)
    resp = await client.get(f"/api/employees/{emp['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == emp["id"]


async def test_get_employee_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/employees/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert resp.status_code == 404


async def test_update_employee_salary(client: AsyncClient, auth_headers: dict):
    emp = await _create_employee(client, auth_headers, basic_salary="50000")
    resp = await client.put(f"/api/employees/{emp['id']}", json={"basic_salary": "60000.00"}, headers=auth_headers)
    assert resp.status_code == 200
    assert Decimal(resp.json()["data"]["basic_salary"]) == Decimal("60000.00")


async def test_update_employee_to_duplicate_employee_no_rejected(client: AsyncClient, auth_headers: dict):
    a = await _create_employee(client, auth_headers)
    b = await _create_employee(client, auth_headers)
    resp = await client.put(f"/api/employees/{b['id']}", json={"employee_no": a["employee_no"]}, headers=auth_headers)
    assert resp.status_code == 409


async def test_delete_employee_soft_deletes(client: AsyncClient, auth_headers: dict):
    emp = await _create_employee(client, auth_headers)
    resp = await client.delete(f"/api/employees/{emp['id']}", headers=auth_headers)
    assert resp.status_code == 200

    get_resp = await client.get(f"/api/employees/{emp['id']}", headers=auth_headers)
    assert get_resp.json()["data"]["status"] == "inactive"


async def test_employees_require_auth(client: AsyncClient):
    resp = await client.get("/api/employees")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Payroll runs — generation correctness (the highest-risk surface: this is
# what computes the actual money employees get paid)
# ---------------------------------------------------------------------------

async def test_create_run_generates_payslip_matching_service_computation(client: AsyncClient, auth_headers: dict):
    emp = await _create_employee(client, auth_headers, basic_salary="30000.00", allowances="0")
    run = await _create_run(client, auth_headers, year=2026, month=1)

    assert run["status"] == "draft"
    assert len(run["payslips"]) == 1
    slip = run["payslips"][0]
    assert slip["employee_id"] == emp["id"]
    assert slip["employee_name"] == emp["full_name"]
    assert slip["employee_no"] == emp["employee_no"]

    expected = payroll_service.compute_payslip(basic_salary=Decimal("30000.00"), allowances=Decimal("0"))
    assert Decimal(slip["gross_pay"]) == expected.gross_pay
    assert Decimal(slip["nssf"]) == expected.nssf
    assert Decimal(slip["shif"]) == expected.shif
    assert Decimal(slip["housing_levy"]) == expected.housing_levy
    assert Decimal(slip["paye"]) == expected.paye
    assert Decimal(slip["total_deductions"]) == expected.total_deductions
    assert Decimal(slip["net_pay"]) == expected.net_pay
    # Net pay must reconcile — this is the number the business actually pays out
    assert Decimal(slip["net_pay"]) == Decimal(slip["gross_pay"]) - Decimal(slip["total_deductions"])


async def test_create_run_covers_every_active_employee_exactly_once(client: AsyncClient, auth_headers: dict):
    e1 = await _create_employee(client, auth_headers, basic_salary="40000")
    e2 = await _create_employee(client, auth_headers, basic_salary="60000")
    run = await _create_run(client, auth_headers, year=2026, month=2)

    employee_ids = {p["employee_id"] for p in run["payslips"]}
    assert employee_ids == {e1["id"], e2["id"]}
    assert len(run["payslips"]) == 2


async def test_create_run_excludes_inactive_employees(client: AsyncClient, auth_headers: dict):
    active = await _create_employee(client, auth_headers, basic_salary="40000")
    inactive = await _create_employee(client, auth_headers, basic_salary="40000")
    await client.delete(f"/api/employees/{inactive['id']}", headers=auth_headers)

    run = await _create_run(client, auth_headers, year=2026, month=3)
    employee_ids = {p["employee_id"] for p in run["payslips"]}
    assert employee_ids == {active["id"]}


async def test_create_run_with_no_active_employees_rejected(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/payroll/runs", json={"period_year": 2026, "period_month": 4}, headers=auth_headers)
    assert resp.status_code == 400


async def test_create_run_duplicate_period_rejected(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers)
    await _create_run(client, auth_headers, year=2026, month=5)
    resp = await client.post("/api/payroll/runs", json={"period_year": 2026, "period_month": 5}, headers=auth_headers)
    assert resp.status_code == 409


async def test_create_run_invalid_month_rejected(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers)
    resp = await client.post("/api/payroll/runs", json={"period_year": 2026, "period_month": 13}, headers=auth_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Payroll runs — list / get / lifecycle
# ---------------------------------------------------------------------------

async def test_list_runs_aggregates_employee_count_and_net_pay(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers, basic_salary="30000")
    await _create_employee(client, auth_headers, basic_salary="50000")
    run = await _create_run(client, auth_headers, year=2026, month=6)

    resp = await client.get("/api/payroll/runs", headers=auth_headers)
    assert resp.status_code == 200
    listed = next(r for r in resp.json() if r["id"] == run["id"])
    assert listed["employee_count"] == 2

    expected_total_net = sum(Decimal(p["net_pay"]) for p in run["payslips"])
    assert Decimal(listed["total_net_pay"]) == expected_total_net


async def test_get_run(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers)
    run = await _create_run(client, auth_headers, year=2026, month=7)
    resp = await client.get(f"/api/payroll/runs/{run['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == run["id"]


async def test_get_run_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/payroll/runs/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert resp.status_code == 404


async def test_finalize_run_locks_it(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers)
    run = await _create_run(client, auth_headers, year=2026, month=8)

    resp = await client.post(f"/api/payroll/runs/{run['id']}/finalize", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "finalized"
    assert data["finalized_at"] is not None


async def test_cannot_finalize_twice(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers)
    run = await _create_run(client, auth_headers, year=2026, month=9)
    await client.post(f"/api/payroll/runs/{run['id']}/finalize", headers=auth_headers)

    resp = await client.post(f"/api/payroll/runs/{run['id']}/finalize", headers=auth_headers)
    assert resp.status_code == 400


async def test_cannot_delete_finalized_run(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers)
    run = await _create_run(client, auth_headers, year=2026, month=10)
    await client.post(f"/api/payroll/runs/{run['id']}/finalize", headers=auth_headers)

    resp = await client.delete(f"/api/payroll/runs/{run['id']}", headers=auth_headers)
    assert resp.status_code == 400


async def test_delete_draft_run(client: AsyncClient, auth_headers: dict):
    await _create_employee(client, auth_headers)
    run = await _create_run(client, auth_headers, year=2026, month=11)

    resp = await client.delete(f"/api/payroll/runs/{run['id']}", headers=auth_headers)
    assert resp.status_code == 200

    get_resp = await client.get(f"/api/payroll/runs/{run['id']}", headers=auth_headers)
    assert get_resp.status_code == 404


async def test_export_csv_contains_payslip_rows(client: AsyncClient, auth_headers: dict):
    emp = await _create_employee(client, auth_headers, basic_salary="35000")
    run = await _create_run(client, auth_headers, year=2026, month=12)

    resp = await client.get(f"/api/payroll/runs/{run['id']}/export/csv", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    body = resp.text
    assert emp["employee_no"] in body
    assert emp["full_name"] in body
    assert "Net Pay" in body


async def test_payroll_runs_require_auth(client: AsyncClient):
    resp = await client.get("/api/payroll/runs")
    assert resp.status_code in (401, 403)


async def test_create_run_requires_auth(client: AsyncClient):
    resp = await client.post("/api/payroll/runs", json={"period_year": 2026, "period_month": 1})
    assert resp.status_code in (401, 403)
