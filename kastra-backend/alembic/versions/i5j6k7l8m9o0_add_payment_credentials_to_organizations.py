"""add_payment_credentials_to_organizations

Revision ID: i5j6k7l8m9o0
Revises: h4i5j6k7l8m9
Create Date: 2026-05-21

"""
from alembic import op
import sqlalchemy as sa

revision = 'i5j6k7l8m9o0'
down_revision = 'h4i5j6k7l8m9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('organizations', sa.Column('paystack_secret_key', sa.String(255), nullable=True))
    op.add_column('organizations', sa.Column('mpesa_consumer_key', sa.String(255), nullable=True))
    op.add_column('organizations', sa.Column('mpesa_consumer_secret', sa.String(255), nullable=True))
    op.add_column('organizations', sa.Column('mpesa_shortcode', sa.String(20), nullable=True))
    op.add_column('organizations', sa.Column('mpesa_passkey', sa.String(255), nullable=True))
    op.add_column('organizations', sa.Column('mpesa_env', sa.String(20), nullable=False, server_default='sandbox'))


def downgrade() -> None:
    op.drop_column('organizations', 'mpesa_env')
    op.drop_column('organizations', 'mpesa_passkey')
    op.drop_column('organizations', 'mpesa_shortcode')
    op.drop_column('organizations', 'mpesa_consumer_secret')
    op.drop_column('organizations', 'mpesa_consumer_key')
    op.drop_column('organizations', 'paystack_secret_key')
