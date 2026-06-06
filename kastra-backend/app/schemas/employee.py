from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    employee_no: str
    full_name: str
    national_id: str | None = None
    kra_pin: str | None = None
    nssf_no: str | None = None
    shif_no: str | None = None
    phone: str | None = None
    email: str | None = None
    job_title: str | None = None
    employment_type: str = "permanent"
    basic_salary: Decimal = Decimal("0")
    allowances: Decimal = Decimal("0")
    bank_name: str | None = None
    bank_account_no: str | None = None
    mpesa_number: str | None = None
    date_joined: date | None = None
    user_id: UUID | None = None


class EmployeeUpdate(BaseModel):
    employee_no: str | None = None
    full_name: str | None = None
    national_id: str | None = None
    kra_pin: str | None = None
    nssf_no: str | None = None
    shif_no: str | None = None
    phone: str | None = None
    email: str | None = None
    job_title: str | None = None
    employment_type: str | None = None
    basic_salary: Decimal | None = None
    allowances: Decimal | None = None
    bank_name: str | None = None
    bank_account_no: str | None = None
    mpesa_number: str | None = None
    date_joined: date | None = None
    status: str | None = None
    user_id: UUID | None = None


class EmployeeOut(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID | None
    employee_no: str
    full_name: str
    national_id: str | None
    kra_pin: str | None
    nssf_no: str | None
    shif_no: str | None
    phone: str | None
    email: str | None
    job_title: str | None
    employment_type: str
    basic_salary: Decimal
    allowances: Decimal
    bank_name: str | None
    bank_account_no: str | None
    mpesa_number: str | None
    date_joined: date | None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
