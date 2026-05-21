"""initial

Revision ID: 82a654d56a8f
Revises:
Create Date: 2026-05-20 09:08:47.964747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '82a654d56a8f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Independent tables ────────────────────────────────────────
    op.create_table('clients',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('address', sa.String(length=500), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_clients_name', 'clients', ['name'], unique=False)
    op.create_index('ix_clients_status', 'clients', ['status'], unique=False)

    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=True),
    sa.Column('display_name', sa.String(length=100), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('google_id', sa.String(length=100), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('google_id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    op.create_table('sequence_counters',
    sa.Column('entity_type', sa.String(length=20), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('last_sequence_number', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('entity_type', 'year')
    )

    # ── invoices: created WITHOUT the quotation_id FK to break the cycle ──
    op.create_table('invoices',
    sa.Column('id', sa.String(length=20), nullable=False),
    sa.Column('quotation_id', sa.String(length=20), nullable=True),
    sa.Column('client_id', sa.UUID(), nullable=False),
    sa.Column('payment_status', sa.String(length=20), nullable=False),
    sa.Column('payment_method', sa.String(length=30), nullable=True),
    sa.Column('subtotal', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('vat_amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('grand_total', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('mpesa_checkout_request_id', sa.String(length=100), nullable=True),
    sa.Column('reminders_sent', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoices_client_id', 'invoices', ['client_id'], unique=False)
    op.create_index('ix_invoices_created_at', 'invoices', ['created_at'], unique=False)
    op.create_index(op.f('ix_invoices_mpesa_checkout_request_id'), 'invoices', ['mpesa_checkout_request_id'], unique=False)
    op.create_index('ix_invoices_payment_status', 'invoices', ['payment_status'], unique=False)

    # ── quotations: can reference invoices now that it exists ─────
    op.create_table('quotations',
    sa.Column('id', sa.String(length=20), nullable=False),
    sa.Column('client_id', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('subtotal', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('vat_amount', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('grand_total', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('converted_to_invoice', sa.Boolean(), nullable=False),
    sa.Column('invoice_id', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quotations_client_id', 'quotations', ['client_id'], unique=False)
    op.create_index('ix_quotations_created_at', 'quotations', ['created_at'], unique=False)
    op.create_index('ix_quotations_status', 'quotations', ['status'], unique=False)

    # ── Now add the deferred FK: invoices.quotation_id → quotations ──
    op.create_foreign_key(
        'fk_invoices_quotation_id',
        'invoices', 'quotations',
        ['quotation_id'], ['id']
    )

    # ── Child tables ──────────────────────────────────────────────
    op.create_table('invoice_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('invoice_id', sa.String(length=20), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('line_total', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoice_items_invoice_id', 'invoice_items', ['invoice_id'], unique=False)

    op.create_table('payment_details',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('invoice_id', sa.String(length=20), nullable=False),
    sa.Column('payment_method', sa.String(length=30), nullable=False),
    sa.Column('payment_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('mpesa_receipt_number', sa.String(length=50), nullable=True),
    sa.Column('transaction_id', sa.String(length=100), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('invoice_id')
    )

    op.create_table('quotation_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('quotation_id', sa.String(length=20), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('line_total', sa.Numeric(precision=15, scale=2), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['quotation_id'], ['quotations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quotation_items_quotation_id', 'quotation_items', ['quotation_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_quotation_items_quotation_id', table_name='quotation_items')
    op.drop_table('quotation_items')
    op.drop_table('payment_details')
    op.drop_index('ix_invoice_items_invoice_id', table_name='invoice_items')
    op.drop_table('invoice_items')
    op.drop_constraint('fk_invoices_quotation_id', 'invoices', type_='foreignkey')
    op.drop_index('ix_quotations_status', table_name='quotations')
    op.drop_index('ix_quotations_created_at', table_name='quotations')
    op.drop_index('ix_quotations_client_id', table_name='quotations')
    op.drop_table('quotations')
    op.drop_index('ix_invoices_payment_status', table_name='invoices')
    op.drop_index(op.f('ix_invoices_mpesa_checkout_request_id'), table_name='invoices')
    op.drop_index('ix_invoices_created_at', table_name='invoices')
    op.drop_index('ix_invoices_client_id', table_name='invoices')
    op.drop_table('invoices')
    op.drop_table('sequence_counters')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index('ix_clients_status', table_name='clients')
    op.drop_index('ix_clients_name', table_name='clients')
    op.drop_table('clients')
