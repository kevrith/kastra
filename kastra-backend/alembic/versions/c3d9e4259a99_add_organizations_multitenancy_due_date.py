"""add_organizations_multitenancy_due_date

Revision ID: c3d9e4259a99
Revises: 82a654d56a8f
Create Date: 2026-05-20 17:15:33.637816

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'c3d9e4259a99'
down_revision: Union[str, None] = '82a654d56a8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create organizations table
    op.create_table('organizations',
        sa.Column('id', UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('kra_pin', sa.String(length=20), nullable=True),
        sa.Column('payment_terms_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    conn = op.get_bind()

    # 2. Add organization_id as NULLABLE first so existing rows don't violate NOT NULL
    for table in ('users', 'clients', 'quotations', 'invoices', 'sequence_counters'):
        op.add_column(table, sa.Column('organization_id', UUID(), nullable=True))

    # 3. due_date on invoices (nullable, no existing data issue)
    op.add_column('invoices', sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))

    # 4. Migrate existing data: create one org per existing user and link everything
    users = conn.execute(sa.text("SELECT id, display_name FROM users")).fetchall()
    for user in users:
        import uuid
        org_id = str(uuid.uuid4())
        conn.execute(
            sa.text("INSERT INTO organizations (id, name, payment_terms_days) VALUES (:id, :name, 30)"),
            {"id": org_id, "name": f"{user.display_name}'s Business"},
        )
        conn.execute(
            sa.text("UPDATE users SET organization_id = :org_id WHERE id = :user_id"),
            {"org_id": org_id, "user_id": str(user.id)},
        )
        # Assign all unlinked clients/quotations/invoices to this user's org
        conn.execute(
            sa.text("UPDATE clients SET organization_id = :org_id WHERE organization_id IS NULL"),
            {"org_id": org_id},
        )
        conn.execute(
            sa.text("UPDATE quotations SET organization_id = :org_id WHERE organization_id IS NULL"),
            {"org_id": org_id},
        )
        conn.execute(
            sa.text("UPDATE invoices SET organization_id = :org_id WHERE organization_id IS NULL"),
            {"org_id": org_id},
        )
        conn.execute(
            sa.text("UPDATE sequence_counters SET organization_id = :org_id WHERE organization_id IS NULL"),
            {"org_id": org_id},
        )

    # 5. Now make the columns NOT NULL
    for table in ('users', 'clients', 'quotations', 'invoices', 'sequence_counters'):
        op.alter_column(table, 'organization_id', nullable=False)

    # 6. Add indexes and foreign keys
    op.create_index('ix_clients_organization_id', 'clients', ['organization_id'], unique=False)
    op.create_index('ix_invoices_organization_id', 'invoices', ['organization_id'], unique=False)
    op.create_index('ix_quotations_organization_id', 'quotations', ['organization_id'], unique=False)
    op.create_index(op.f('ix_users_organization_id'), 'users', ['organization_id'], unique=False)

    op.create_foreign_key('fk_clients_org', 'clients', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('fk_invoices_org', 'invoices', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('fk_quotations_org', 'quotations', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('fk_seq_counters_org', 'sequence_counters', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('fk_users_org', 'users', 'organizations', ['organization_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_users_org', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_organization_id'), table_name='users')
    op.drop_column('users', 'organization_id')

    op.drop_constraint('fk_seq_counters_org', 'sequence_counters', type_='foreignkey')
    op.drop_column('sequence_counters', 'organization_id')

    op.drop_constraint('fk_quotations_org', 'quotations', type_='foreignkey')
    op.drop_index('ix_quotations_organization_id', table_name='quotations')
    op.drop_column('quotations', 'organization_id')

    op.drop_constraint('fk_invoices_org', 'invoices', type_='foreignkey')
    op.drop_index('ix_invoices_organization_id', table_name='invoices')
    op.drop_column('invoices', 'due_date')
    op.drop_column('invoices', 'organization_id')

    op.drop_constraint('fk_clients_org', 'clients', type_='foreignkey')
    op.drop_index('ix_clients_organization_id', table_name='clients')
    op.drop_column('clients', 'organization_id')

    op.drop_table('organizations')
