"""add user_permissions table

Revision ID: z1a2b3c4d5e6
Revises: w9x0y1z2a3b4
Create Date: 2026-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'z1a2b3c4d5e6'
down_revision = 'x0y1z2a3b4c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_permissions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('can_view_invoices', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_create_invoices', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_edit_invoices', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_delete_invoices', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_view_quotations', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_create_quotations', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_edit_quotations', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_delete_quotations', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_view_clients', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_create_clients', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_edit_clients', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_delete_clients', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_view_reports', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_view_expenses', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_create_expenses', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_view_projects', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_manage_projects', sa.Boolean(), nullable=False, server_default='false'),
        sa.UniqueConstraint('user_id', name='uq_user_permissions_user_id'),
    )


def downgrade() -> None:
    op.drop_table('user_permissions')
