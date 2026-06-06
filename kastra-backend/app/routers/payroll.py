import csv
import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_manager_or_above
from app.models.employee import Employee
from app.models.organization import Organization
from app.models.payroll import PayrollRun, Payslip
from app.models.user import User
from app.schemas.common import MessageResponse, Response
from app.schemas.payroll import PayrollRunCreate, PayrollRunListItem, PayrollRunOut, PayslipOut
from app.services import payroll_service
from app.services.pdf_service import generate_payslip_pdf

router = APIRouter(prefix="/api/payroll", tags=["payroll"])

_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


async def _get_run(db: AsyncSession, run_id: uuid.UUID, organization_id: uuid.UUID) -> PayrollRun:
    run = await db.get(PayrollRun, run_id, options=[selectinload(PayrollRun.payslips)])
    if not run or run.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    return run


@router.get("/runs", response_model=list[PayrollRunListItem])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(
            PayrollRun,
            func.count(Payslip.id).label("employee_count"),
            func.coalesce(func.sum(Payslip.net_pay), 0).label("total_net_pay"),
        )
        .outerjoin(Payslip, Payslip.payroll_run_id == PayrollRun.id)
        .where(PayrollRun.organization_id == current_user.organization_id)
        .group_by(PayrollRun.id)
        .order_by(PayrollRun.period_year.desc(), PayrollRun.period_month.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        PayrollRunListItem(
            id=run.id,
            period_year=run.period_year,
            period_month=run.period_month,
            status=run.status,
            finalized_at=run.finalized_at,
            created_at=run.created_at,
            employee_count=employee_count,
            total_net_pay=total_net_pay,
        )
        for run, employee_count, total_net_pay in rows
    ]


@router.post("/runs", response_model=Response[PayrollRunOut], status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: PayrollRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_above),
):
    if not (1 <= payload.period_month <= 12):
        raise HTTPException(status_code=400, detail="period_month must be between 1 and 12")

    existing = (
        await db.execute(
            select(PayrollRun).where(
                PayrollRun.organization_id == current_user.organization_id,
                PayrollRun.period_year == payload.period_year,
                PayrollRun.period_month == payload.period_month,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="A payroll run already exists for this period")

    employees = (
        await db.execute(
            select(Employee).where(
                Employee.organization_id == current_user.organization_id,
                Employee.status == "active",
            )
        )
    ).scalars().all()
    if not employees:
        raise HTTPException(status_code=400, detail="No active employees to run payroll for")

    run = PayrollRun(
        organization_id=current_user.organization_id,
        period_year=payload.period_year,
        period_month=payload.period_month,
        notes=payload.notes,
    )
    db.add(run)
    await db.flush()

    for emp in employees:
        result = payroll_service.compute_payslip(
            basic_salary=Decimal(emp.basic_salary),
            allowances=Decimal(emp.allowances),
        )
        db.add(Payslip(
            payroll_run_id=run.id,
            employee_id=emp.id,
            employee_name=emp.full_name,
            employee_no=emp.employee_no,
            basic_salary=Decimal(emp.basic_salary),
            allowances=Decimal(emp.allowances),
            gross_pay=result.gross_pay,
            taxable_income=result.taxable_income,
            paye=result.paye,
            personal_relief=result.personal_relief,
            nssf=result.nssf,
            shif=result.shif,
            housing_levy=result.housing_levy,
            other_deductions=result.other_deductions,
            total_deductions=result.total_deductions,
            net_pay=result.net_pay,
        ))

    await db.flush()
    run = await _get_run(db, run.id, current_user.organization_id)
    return Response(data=run)


@router.get("/runs/{run_id}", response_model=Response[PayrollRunOut])
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = await _get_run(db, run_id, current_user.organization_id)
    return Response(data=run)


@router.post("/runs/{run_id}/finalize", response_model=Response[PayrollRunOut])
async def finalize_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_above),
):
    run = await _get_run(db, run_id, current_user.organization_id)
    if run.status == "finalized":
        raise HTTPException(status_code=400, detail="Payroll run is already finalized")
    run.status = "finalized"
    run.finalized_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(run)
    return Response(data=run)


@router.delete("/runs/{run_id}", response_model=MessageResponse)
async def delete_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_above),
):
    run = await _get_run(db, run_id, current_user.organization_id)
    if run.status == "finalized":
        raise HTTPException(status_code=400, detail="Finalized payroll runs cannot be deleted")
    await db.delete(run)
    return MessageResponse(message="Payroll run deleted")


@router.get("/runs/{run_id}/export/csv")
async def export_run_csv(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = await _get_run(db, run_id, current_user.organization_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Employee No", "Name", "Basic Salary", "Allowances", "Gross Pay",
        "Taxable Income", "PAYE", "Personal Relief", "NSSF", "SHIF",
        "Housing Levy", "Other Deductions", "Total Deductions", "Net Pay",
    ])
    for p in run.payslips:
        writer.writerow([
            p.employee_no, p.employee_name, p.basic_salary, p.allowances, p.gross_pay,
            p.taxable_income, p.paye, p.personal_relief, p.nssf, p.shif,
            p.housing_levy, p.other_deductions, p.total_deductions, p.net_pay,
        ])

    output.seek(0)
    period_label = f"{run.period_year}-{run.period_month:02d}"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=kastra-payroll-register-{period_label}.csv"},
    )


@router.get("/runs/{run_id}/payslips/{payslip_id}/pdf")
async def download_payslip_pdf(
    run_id: uuid.UUID,
    payslip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = await _get_run(db, run_id, current_user.organization_id)
    payslip = next((p for p in run.payslips if p.id == payslip_id), None)
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")

    org = await db.get(Organization, current_user.organization_id)

    payslip_dict = PayslipOut.model_validate(payslip).model_dump(mode="json")
    run_dict = {"period_year": run.period_year, "period_month": run.period_month}
    org_dict = {
        "name": org.name,
        "address": org.address,
        "kra_pin": org.kra_pin,
        "logo_url": org.logo_url,
    }

    pdf_bytes = await generate_payslip_pdf(payslip_dict, run_dict, org_dict)
    period_label = f"{_MONTH_NAMES[run.period_month]}-{run.period_year}"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="payslip-{payslip.employee_no}-{period_label}.pdf"'},
    )
