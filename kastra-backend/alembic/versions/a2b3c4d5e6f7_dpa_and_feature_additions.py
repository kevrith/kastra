"""dpa_and_feature_additions

Adds:
  - users.consented_at       — Kenya DPA 2019 consent timestamp
  - quotations.expires_at    — quotation expiry dates
  - audit_logs table         — immutable financial audit trail (DPA accountability)

Revision ID: a2b3c4d5e6f7
Revises: f7c8d9e0a1b2
Create Date: 2026-05-20 19:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'f7c8d9e0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Kenya DPA 2019 — consent timestamp
    op.add_column('users', sa.Column('consented_at', sa.DateTime(timezone=True), nullable=True))

    # Quotation expiry dates
    op.add_column('quotations', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))

    # Immutable audit log for financial accountability
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', sa.String(50), nullable=True, index=True),
        sa.Column('user_id', sa.String(50), nullable=True, index=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_column('quotations', 'expires_at')
    op.drop_column('users', 'consented_at')
