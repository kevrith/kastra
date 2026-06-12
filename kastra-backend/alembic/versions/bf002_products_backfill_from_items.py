"""One-time backfill of the products catalog from existing quotation/invoice items.

This previously ran in the FastAPI lifespan hook on every boot (full scan of all
document items, once per worker). It belongs in a migration: run once, recorded,
done. Ongoing catalog sync happens inline when documents are created
(see _upsert_products in routers/invoices.py and routers/quotations.py).

Revision ID: bf002_products_backfill
Revises: rls001_enable_rls_on_all_tables
Create Date: 2026-06-12
"""

from alembic import op

revision = "bf002_products_backfill"
down_revision = "rls001_enable_rls_on_all_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO products (id, organization_id, name, unit_price)
        SELECT gen_random_uuid(), organization_id, name, unit_price
        FROM (
            SELECT DISTINCT ON (src.organization_id, LEFT(src.description, 200))
                src.organization_id,
                LEFT(src.description, 200) AS name,
                src.unit_price
            FROM (
                SELECT q.organization_id, qi.description, qi.unit_price
                FROM quotation_items qi JOIN quotations q ON q.id = qi.quotation_id
                UNION ALL
                SELECT i.organization_id, ii.description, ii.unit_price
                FROM invoice_items ii JOIN invoices i ON i.id = ii.invoice_id
            ) src
            WHERE src.description IS NOT NULL AND src.description <> ''
        ) deduped
        ON CONFLICT (organization_id, name)
        DO UPDATE SET unit_price = EXCLUDED.unit_price
        """
    )


def downgrade() -> None:
    # Data backfill — nothing sensible to undo.
    pass
