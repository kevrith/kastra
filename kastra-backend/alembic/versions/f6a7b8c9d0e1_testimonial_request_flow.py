"""add testimonial request flow columns

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-08 00:01:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    # Make role / text / stars nullable (existing rows keep their values)
    op.alter_column("testimonials", "role",  existing_type=sa.String(150), nullable=True)
    op.alter_column("testimonials", "text",  existing_type=sa.Text,        nullable=True)
    op.alter_column("testimonials", "stars", existing_type=sa.Integer,     nullable=True)

    # Request-flow columns
    op.add_column("testimonials", sa.Column("status", sa.String(20), nullable=False, server_default="approved"))
    op.add_column("testimonials", sa.Column("request_token", sa.String(64), nullable=True))
    op.add_column("testimonials", sa.Column("requested_email", sa.String(255), nullable=True))
    op.add_column("testimonials", sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("testimonials", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("testimonials", sa.Column("consent", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("testimonials", sa.Column("rejection_reason", sa.Text(), nullable=True))

    op.create_unique_constraint("uq_testimonials_request_token", "testimonials", ["request_token"])
    op.create_index("ix_testimonials_request_token", "testimonials", ["request_token"])


def downgrade():
    op.drop_index("ix_testimonials_request_token", "testimonials")
    op.drop_constraint("uq_testimonials_request_token", "testimonials")
    op.drop_column("testimonials", "rejection_reason")
    op.drop_column("testimonials", "consent")
    op.drop_column("testimonials", "submitted_at")
    op.drop_column("testimonials", "requested_at")
    op.drop_column("testimonials", "requested_email")
    op.drop_column("testimonials", "request_token")
    op.drop_column("testimonials", "status")
    op.alter_column("testimonials", "stars", existing_type=sa.Integer,     nullable=False)
    op.alter_column("testimonials", "text",  existing_type=sa.Text,        nullable=False)
    op.alter_column("testimonials", "role",  existing_type=sa.String(150), nullable=False)
