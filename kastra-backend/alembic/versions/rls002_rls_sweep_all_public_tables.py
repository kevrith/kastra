"""enable RLS on every public table, including ones added since rls001

Revision ID: rls002_rls_sweep
Revises: p1q2r3s4t5u6
Create Date: 2026-08-25 00:00:00.000000

rls001 enabled RLS from a hard-coded table list. Every migration since then
that created a table left it without RLS — credit_notes, credit_note_items,
delivery_notes, delivery_note_items, purchase_orders, purchase_order_items,
purchase_order_notes, goods_receipts, goods_receipt_items, supplier_bills and
supplier_price_history were all readable and writable through Supabase's
PostgREST endpoint by anyone with the anon key.

This replaces the list with a dynamic sweep (see app.db_rls). env.py also runs
the sweep after every upgrade, so the drift cannot come back.
"""
from alembic import op

from app.db_rls import ENABLE_RLS_ON_PUBLIC_TABLES

revision = "rls002_rls_sweep"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(ENABLE_RLS_ON_PUBLIC_TABLES)


def downgrade() -> None:
    # Intentionally a no-op. Disabling RLS would re-expose every table in the
    # public schema through PostgREST; there is no state here worth reverting.
    pass
