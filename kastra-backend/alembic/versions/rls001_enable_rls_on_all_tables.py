"""enable RLS on all public tables

Revision ID: rls001_enable_rls_on_all_tables
Revises: g7h8i9j0k1l2
Create Date: 2026-06-12 00:00:00.000000

All public-schema tables are exposed to Supabase's PostgREST layer by default.
Enabling RLS with no permissive policies for anon/authenticated denies all
direct PostgREST access while leaving the FastAPI backend unaffected — it
connects as the postgres superuser which bypasses RLS unconditionally.
"""
from alembic import op

revision = "rls001_enable_rls_on_all_tables"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None

# Tables created by this project's migrations.
# alembic_version is included so PostgREST cannot read migration state.
TABLES = [
    "alembic_version",
    "admin_audit_log",
    "affiliate_commissions",
    "affiliate_payouts",
    "affiliate_referrals",
    "affiliates",
    "audit_logs",
    "client_prices",
    "clients",
    "employees",
    "expenses",
    "invoice_charges",
    "invoice_items",
    "invoice_payments",
    "invoices",
    "notifications",
    "organizations",
    "payment_details",
    "payroll_runs",
    "payslips",
    "products",
    "project_photos",
    "projects",
    "project_updates",
    "quotation_charges",
    "quotation_items",
    "quotation_notes",
    "quotations",
    "recurring_invoices",
    "sequence_counters",
    "subscription_payments",
    "supplier_request_invites",
    "supplier_request_items",
    "supplier_requests",
    "supplier_response_items",
    "suppliers",
    "testimonials",
    "user_permissions",
    "users",
]


def upgrade() -> None:
    for table in TABLES:
        # IF EXISTS guards against tables dropped in a later migration
        op.execute(
            f"ALTER TABLE IF EXISTS public.{table} ENABLE ROW LEVEL SECURITY"
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(
            f"ALTER TABLE IF EXISTS public.{table} DISABLE ROW LEVEL SECURITY"
        )
