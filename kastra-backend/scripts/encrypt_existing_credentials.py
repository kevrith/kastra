"""One-time script: encrypt plain-text credential columns for all organisations.

Run ONCE after deploying the FIELD_ENCRYPTION_KEY and running the Alembic migration:

    cd kastra-backend
    python -m scripts.encrypt_existing_credentials

The script is idempotent — values that are already encrypted (valid Fernet tokens) are
left untouched, so it is safe to re-run.
"""
import asyncio
import os
import sys

# Ensure the backend package is importable when run as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

COLUMNS = [
    "paystack_secret_key",
    "mpesa_consumer_key",
    "mpesa_consumer_secret",
    "mpesa_passkey",
    "etims_auth_token",
]


def _is_already_encrypted(value: str, f: Fernet) -> bool:
    try:
        f.decrypt(value.encode())
        return True
    except (InvalidToken, Exception):
        return False


async def run():
    key_raw = os.environ.get("FIELD_ENCRYPTION_KEY", "").strip()
    if not key_raw:
        print("ERROR: FIELD_ENCRYPTION_KEY is not set. Aborting.")
        sys.exit(1)

    fernet = Fernet(key_raw.encode())

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL is not set. Aborting.")
        sys.exit(1)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    db_url = db_url.replace("sslmode=require", "ssl=require")

    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            text("SELECT id, " + ", ".join(COLUMNS) + " FROM organizations")
        )
        rows = result.fetchall()

        updated = 0
        for row in rows:
            org_id = row[0]
            updates = {}
            for i, col in enumerate(COLUMNS):
                value = row[i + 1]
                if value and not _is_already_encrypted(value, fernet):
                    updates[col] = fernet.encrypt(value.encode()).decode()

            if updates:
                set_clause = ", ".join(f"{col} = :{col}" for col in updates)
                await session.execute(
                    text(f"UPDATE organizations SET {set_clause} WHERE id = :id"),
                    {**updates, "id": str(org_id)},
                )
                updated += 1

        await session.commit()
        print(f"Done. Encrypted credentials for {updated} organisation(s) out of {len(rows)} total.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
