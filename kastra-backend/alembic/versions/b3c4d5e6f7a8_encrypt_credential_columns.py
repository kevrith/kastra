"""encrypt credential columns — widen to TEXT and backfill encrypted values

Revision ID: b3c4d5e6f7a8
Revises: z1a2b3c4d5e6
Create Date: 2026-06-11 00:00:00.000000
"""
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = "b3c4d5e6f7a8"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None

COLUMNS = [
    "paystack_secret_key",
    "mpesa_consumer_key",
    "mpesa_consumer_secret",
    "mpesa_passkey",
    "etims_auth_token",
]


def _get_fernet():
    """Return a Fernet instance if FIELD_ENCRYPTION_KEY is set, else None."""
    try:
        from cryptography.fernet import Fernet
        key = os.environ.get("FIELD_ENCRYPTION_KEY", "").strip()
        if not key:
            return None
        return Fernet(key.encode())
    except Exception:
        return None


def _is_already_encrypted(value: str, fernet) -> bool:
    try:
        fernet.decrypt(value.encode())
        return True
    except Exception:
        return False


def upgrade():
    # Step 1 — widen columns from VARCHAR(255) to TEXT
    for col in COLUMNS:
        op.alter_column(
            "organizations",
            col,
            existing_type=sa.String(255),
            type_=sa.Text(),
            existing_nullable=True,
        )

    # Step 2 — encrypt any existing plain-text values in-place
    fernet = _get_fernet()
    if fernet is None:
        return  # No key set — skip backfill (dev environment)

    conn = op.get_bind()
    rows = conn.execute(
        text("SELECT id, " + ", ".join(COLUMNS) + " FROM organizations")
    ).fetchall()

    for row in rows:
        org_id = row[0]
        updates = {}
        for i, col in enumerate(COLUMNS):
            value = row[i + 1]
            if value and not _is_already_encrypted(value, fernet):
                updates[col] = fernet.encrypt(value.encode()).decode()

        if updates:
            set_clause = ", ".join(f"{col} = :{col}" for col in updates)
            conn.execute(
                text(f"UPDATE organizations SET {set_clause} WHERE id = :id"),
                {**updates, "id": str(org_id)},
            )


def downgrade():
    for col in COLUMNS:
        op.alter_column(
            "organizations",
            col,
            existing_type=sa.Text(),
            type_=sa.String(255),
            existing_nullable=True,
        )
