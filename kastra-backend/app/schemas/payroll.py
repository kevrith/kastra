from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PayrollRunCreate(BaseModel):
    period_year: int
    period_month: int
    notes: str | None = None


class PayrollRunUpdate(BaseModel):
    notes: str | None = None


class PayslipOut(BaseModel):
    id: UUID
    payroll_run_id: UUID
    employee_id: UUID
    employee_name: str
    employee_no: str
    basic_salary: Decimal
    allowances: Decimal
    gross_pay: Decimal
    taxable_income: Decimal
    paye: Decimal
    personal_relief: Decimal
    nssf: Decimal
    shif: Decimal
    housing_levy: Decimal
    other_deductions: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class PayrollRunOut(BaseModel):
    id: UUID
    organization_id: UUID
    period_year: int
    period_month: int
    status: str
    notes: str | None
    finalized_at: datetime | None
    created_at: datetime
    updated_at: datetime
    payslips: list[PayslipOut] = []

    class Config:
        from_attributes = True


class PayrollRunListItem(BaseModel):
    id: UUID
    period_year: int
    period_month: int
    status: str
    finalized_at: datetime | None
    created_at: datetime
    employee_count: int = 0
    total_net_pay: Decimal = Decimal("0")

    class Config:
        from_attributes = True
