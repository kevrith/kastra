import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        Index("ix_employees_organization_id", "organization_id"),
        UniqueConstraint("organization_id", "employee_no", name="uq_employees_org_employee_no"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    employee_no: Mapped[str] = mapped_column(String(20), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    national_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    kra_pin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nssf_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
    shif_no: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[str] = mapped_column(String(20), nullable=False, default="permanent")  # permanent | contract | casual
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    allowances: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_account_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mpesa_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_joined: Mapped[date | None] = mapped_column(Date(), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active | inactive
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="employees")  # noqa: F821
    user: Mapped["User | None"] = relationship()  # noqa: F821
    payslips: Mapped[list["Payslip"]] = relationship(back_populates="employee")  # noqa: F821
