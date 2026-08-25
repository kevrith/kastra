"""Every table the models define must be covered by the RLS sweep.

Supabase serves public-schema tables over PostgREST, so a table without RLS is
readable and writable by anyone holding the anon key. rls001 enabled RLS from a
hard-coded list and every table added afterwards was missed; this test fails if
the sweep in app.db_rls ever stops covering the full model surface.
"""
from sqlalchemy import text

from app.database import Base
from app.db_rls import ENABLE_RLS_ON_PUBLIC_TABLES
from tests.conftest import engine

UNPROTECTED_TABLES = """
    SELECT c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind IN ('r', 'p')
      AND NOT c.relrowsecurity
"""


async def test_sweep_enables_rls_on_every_model_table():
    async with engine.begin() as conn:
        await conn.execute(text(ENABLE_RLS_ON_PUBLIC_TABLES))

    async with engine.connect() as conn:
        result = await conn.execute(text(UNPROTECTED_TABLES))
        unprotected = {row[0] for row in result}

    exposed = sorted(set(Base.metadata.tables) & unprotected)
    assert not exposed, f"tables reachable via PostgREST without RLS: {exposed}"


async def test_sweep_is_idempotent():
    """Runs after every alembic upgrade, so a second pass must be a no-op."""
    async with engine.begin() as conn:
        await conn.execute(text(ENABLE_RLS_ON_PUBLIC_TABLES))
        await conn.execute(text(ENABLE_RLS_ON_PUBLIC_TABLES))
