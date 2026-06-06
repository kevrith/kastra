"""add employees, payroll_runs, payslips tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-06 00:00:00.000000

"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("employee_no", sa.String(length=20), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("national_id", sa.String(length=30), nullable=True),
        sa.Column("kra_pin", sa.String(length=20), nullable=True),
        sa.Column("nssf_no", sa.String(length=30), nullable=True),
        sa.Column("shif_no", sa.String(length=30), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("job_title", sa.String(length=100), nullable=True),
        sa.Column("employment_type", sa.String(length=20), nullable=False, server_default="permanent"),
        sa.Column("basic_salary", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("allowances", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("bank_name", sa.String(length=100), nullable=True),
        sa.Column("bank_account_no", sa.String(length=50), nullable=True),
        sa.Column("mpesa_number", sa.String(length=20), nullable=True),
        sa.Column("date_joined", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_employees_organization_id", "employees", ["organization_id"])
    op.create_unique_constraint("uq_employees_org_employee_no", "employees", ["organization_id", "employee_no"])

    op.create_table(
        "payroll_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payroll_runs_organization_id", "payroll_runs", ["organization_id"])
    op.create_unique_constraint(
        "uq_payroll_runs_org_period", "payroll_runs", ["organization_id", "period_year", "period_month"]
    )

    op.create_table(
        "payslips",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("payroll_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payroll_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("employee_name", sa.String(length=150), nullable=False),
        sa.Column("employee_no", sa.String(length=20), nullable=False),
        sa.Column("basic_salary", sa.Numeric(15, 2), nullable=False),
        sa.Column("allowances", sa.Numeric(15, 2), nullable=False),
        sa.Column("gross_pay", sa.Numeric(15, 2), nullable=False),
        sa.Column("taxable_income", sa.Numeric(15, 2), nullable=False),
        sa.Column("paye", sa.Numeric(15, 2), nullable=False),
        sa.Column("personal_relief", sa.Numeric(15, 2), nullable=False),
        sa.Column("nssf", sa.Numeric(15, 2), nullable=False),
        sa.Column("shif", sa.Numeric(15, 2), nullable=False),
        sa.Column("housing_levy", sa.Numeric(15, 2), nullable=False),
        sa.Column("other_deductions", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("total_deductions", sa.Numeric(15, 2), nullable=False),
        sa.Column("net_pay", sa.Numeric(15, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payslips_payroll_run_id", "payslips", ["payroll_run_id"])
    op.create_index("ix_payslips_employee_id", "payslips", ["employee_id"])


def downgrade() -> None:
    op.drop_table("payslips")
    op.drop_table("payroll_runs")
    op.drop_table("employees")
