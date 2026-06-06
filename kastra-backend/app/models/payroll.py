import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PayrollRun(Base):
    __tablename__ = "payroll_runs"
    __table_args__ = (
        Index("ix_payroll_runs_organization_id", "organization_id"),
        UniqueConstraint("organization_id", "period_year", "period_month", name="uq_payroll_runs_org_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft | finalized
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship(back_populates="payroll_runs")  # noqa: F821
    payslips: Mapped[list["Payslip"]] = relationship(
        back_populates="payroll_run", cascade="all, delete-orphan", order_by="Payslip.employee_name"
    )


class Payslip(Base):
    __tablename__ = "payslips"
    __table_args__ = (
        Index("ix_payslips_payroll_run_id", "payroll_run_id"),
        Index("ix_payslips_employee_id", "employee_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payroll_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    # Snapshot fields — preserve payslip values even if the employee record changes later
    employee_name: Mapped[str] = mapped_column(String(150), nullable=False)
    employee_no: Mapped[str] = mapped_column(String(20), nullable=False)
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    allowances: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    taxable_income: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    paye: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    personal_relief: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    nssf: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    shif: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    housing_levy: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    payroll_run: Mapped["PayrollRun"] = relationship(back_populates="payslips")
    employee: Mapped["Employee"] = relationship(back_populates="payslips")  # noqa: F821
