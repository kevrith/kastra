"""restore_dropped_tables

Revision ID: f9a1b2c3d4e5
Revises: e5c6dbc46584
Create Date: 2026-06-04 08:00:00.000000

Restores subscription_payments, admin_audit_log, and quotation_notes which
were incorrectly dropped by e5c6dbc46584 but are still used by the app.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'f9a1b2c3d4e5'
down_revision: Union[str, None] = 'e5c6dbc46584'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'subscription_payments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('org_name', sa.VARCHAR(length=200), server_default=sa.text("''::character varying"), nullable=False),
        sa.Column('amount_kes', sa.INTEGER(), nullable=False),
        sa.Column('plan', sa.VARCHAR(length=20), nullable=False),
        sa.Column('payment_method', sa.VARCHAR(length=20), nullable=False),
        sa.Column('reference', sa.VARCHAR(length=150), nullable=True),
        sa.Column('status', sa.VARCHAR(length=20), server_default=sa.text("'completed'::character varying"), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='subscription_payments_organization_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='subscription_payments_pkey'),
    )
    op.create_index('ix_sub_payments_org', 'subscription_payments', ['organization_id'], unique=False)
    op.create_index('ix_sub_payments_created', 'subscription_payments', ['created_at'], unique=False)

    op.create_table(
        'admin_audit_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('action', sa.VARCHAR(length=50), nullable=False),
        sa.Column('target_org_id', sa.VARCHAR(length=36), nullable=False),
        sa.Column('target_org_name', sa.VARCHAR(length=200), server_default=sa.text("''::character varying"), nullable=False),
        sa.Column('details', sa.TEXT(), nullable=True),
        sa.Column('performed_by', sa.VARCHAR(length=50), server_default=sa.text("'superadmin'::character varying"), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id', name='admin_audit_log_pkey'),
    )
    op.create_index('ix_audit_log_org', 'admin_audit_log', ['target_org_id'], unique=False)
    op.create_index('ix_audit_log_created', 'admin_audit_log', ['created_at'], unique=False)

    op.create_table(
        'quotation_notes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('quotation_id', sa.VARCHAR(length=20), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('body', sa.TEXT(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='quotation_notes_created_by_fkey'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='quotation_notes_organization_id_fkey'),
        sa.ForeignKeyConstraint(['quotation_id'], ['quotations.id'], name='quotation_notes_quotation_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='quotation_notes_pkey'),
    )
    op.create_index('ix_quotation_notes_quotation_id', 'quotation_notes', ['quotation_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_quotation_notes_quotation_id', table_name='quotation_notes')
    op.drop_table('quotation_notes')
    op.drop_index('ix_audit_log_created', table_name='admin_audit_log')
    op.drop_index('ix_audit_log_org', table_name='admin_audit_log')
    op.drop_table('admin_audit_log')
    op.drop_index('ix_sub_payments_created', table_name='subscription_payments')
    op.drop_index('ix_sub_payments_org', table_name='subscription_payments')
    op.drop_table('subscription_payments')
