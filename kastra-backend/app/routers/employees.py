import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_manager_or_above
from app.models.employee import Employee
from app.models.user import User
from app.schemas.common import MessageResponse, Response
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeOut])
async def list_employees(
    q: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Employee).where(Employee.organization_id == current_user.organization_id)
    if status_filter:
        stmt = stmt.where(Employee.status == status_filter)
    else:
        stmt = stmt.where(Employee.status == "active")
    if q:
        stmt = stmt.where(
            (Employee.full_name.ilike(f"%{q}%")) | (Employee.employee_no.ilike(f"%{q}%"))
        )
    rows = (await db.execute(stmt.order_by(Employee.full_name))).scalars().all()
    return rows


@router.post("", response_model=Response[EmployeeOut], status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_above),
):
    existing = (
        await db.execute(
            select(Employee).where(
                Employee.organization_id == current_user.organization_id,
                Employee.employee_no == payload.employee_no,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="An employee with this employee number already exists")

    emp = Employee(
        organization_id=current_user.organization_id,
        **payload.model_dump(),
    )
    db.add(emp)
    await db.flush()
    await db.refresh(emp)
    return Response(data=emp)


@router.get("/{employee_id}", response_model=Response[EmployeeOut])
async def get_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = await db.get(Employee, employee_id)
    if not emp or emp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    return Response(data=emp)


@router.put("/{employee_id}", response_model=Response[EmployeeOut])
async def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_above),
):
    emp = await db.get(Employee, employee_id)
    if not emp or emp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Employee not found")

    data = payload.model_dump(exclude_unset=True)
    if "employee_no" in data and data["employee_no"] != emp.employee_no:
        existing = (
            await db.execute(
                select(Employee).where(
                    Employee.organization_id == current_user.organization_id,
                    Employee.employee_no == data["employee_no"],
                    Employee.id != employee_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="An employee with this employee number already exists")

    for field, value in data.items():
        setattr(emp, field, value)

    await db.flush()
    await db.refresh(emp)
    return Response(data=emp)


@router.delete("/{employee_id}", response_model=MessageResponse)
async def delete_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_above),
):
    emp = await db.get(Employee, employee_id)
    if not emp or emp.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    emp.status = "inactive"
    return MessageResponse(message="Employee removed")
