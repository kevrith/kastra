"""add unique constraint on products(organization_id, name)

Revision ID: t6u7v8w9x0y1
Revises: s5t6u7v8w9x0
Create Date: 2026-05-21
"""
from alembic import op

revision = "t6u7v8w9x0y1"
down_revision = "s5t6u7v8w9x0"
branch_labels = None
depends_on = None


def upgrade():
    # Remove duplicate (org, name) rows keeping the most recently updated one
    op.execute("""
        DELETE FROM products p1
        USING products p2
        WHERE p1.organization_id = p2.organization_id
          AND p1.name = p2.name
          AND p1.updated_at < p2.updated_at
    """)
    op.create_unique_constraint("uq_product_org_name", "products", ["organization_id", "name"])


def downgrade():
    op.drop_constraint("uq_product_org_name", "products", type_="unique")
