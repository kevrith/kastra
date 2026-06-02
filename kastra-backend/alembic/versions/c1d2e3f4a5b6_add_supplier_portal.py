"""add supplier portal: suppliers, supplier_requests, invites, response items

Revision ID: c1d2e3f4a5b6
Revises: b9c8d7e6f5a4
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "c1d2e3f4a5b6"
down_revision = "b9c8d7e6f5a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_suppliers_organization_id", "suppliers", ["organization_id"])

    op.create_table(
        "supplier_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_supplier_requests_organization_id", "supplier_requests", ["organization_id"])

    op.create_table(
        "supplier_request_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", UUID(as_uuid=True), sa.ForeignKey("supplier_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0"),
    )
    op.create_index("ix_supplier_request_items_request_id", "supplier_request_items", ["request_id"])

    op.create_table(
        "supplier_request_invites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", UUID(as_uuid=True), sa.ForeignKey("supplier_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("portal_token", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supplier_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_supplier_request_invites_request_id", "supplier_request_invites", ["request_id"])
    op.create_index("ix_supplier_request_invites_portal_token", "supplier_request_invites", ["portal_token"], unique=True)

    op.create_table(
        "supplier_response_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("invite_id", UUID(as_uuid=True), sa.ForeignKey("supplier_request_invites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0"),
    )
    op.create_index("ix_supplier_response_items_invite_id", "supplier_response_items", ["invite_id"])


def downgrade() -> None:
    op.drop_table("supplier_response_items")
    op.drop_table("supplier_request_invites")
    op.drop_table("supplier_request_items")
    op.drop_table("supplier_requests")
    op.drop_table("suppliers")
