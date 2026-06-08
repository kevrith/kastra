"""add testimonials table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-08 00:00:00.000000
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "testimonials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(150), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("stars", sa.Integer, nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Seed with the original hardcoded testimonials so the landing page
    # never shows an empty section on a fresh deployment.
    op.execute(sa.text("""
        INSERT INTO testimonials (id, name, role, text, stars, is_active, sort_order)
        VALUES
          (
            '11111111-aaaa-bbbb-cccc-111111111111',
            'Grace Wanjiku',
            'CEO, Wanjiku Consulting',
            'Kastra transformed how we invoice clients. What used to take hours now takes minutes. M-Pesa integration alone saved us so much chasing of payments.',
            5, true, 0
          ),
          (
            '22222222-aaaa-bbbb-cccc-222222222222',
            'David Otieno',
            'Director, Otieno Supplies Ltd',
            'The eTIMS compliance feature is a game changer. We are always audit-ready and the dashboard gives us a clear picture of our finances every morning.',
            5, true, 1
          ),
          (
            '33333333-aaaa-bbbb-cccc-333333333333',
            'Amina Hassan',
            'Founder, Amina Events',
            'I used to juggle spreadsheets and WhatsApp for quotations. Kastra made me look like a proper enterprise from day one.',
            5, true, 2
          )
    """))


def downgrade():
    op.drop_table("testimonials")
