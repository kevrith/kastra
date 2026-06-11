import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.utils.rate_limit import limiter

# Disable rate limiting in tests so fixture registrations don't hit 429.
limiter.enabled = False

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://kastra_user:REMOVED_SEE_GITHUB_SECRETS@localhost:5432/kastra_test",
)

# NullPool: no connection pooling. Each operation gets a fresh connection so
# connections are never shared across event loops (each test gets its own loop).
engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _wipe_and_create():
    """Drop and recreate public schema, then create all tables from models."""
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO kastra_user"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        await conn.commit()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Run the schema setup synchronously before any test collection so we don't
# have to wrestle with cross-scope event-loop ownership.
asyncio.run(_wipe_and_create())


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_counter = {"n": 0}


async def _register_and_verify(client: AsyncClient, db_session: AsyncSession, email: str, password: str, n: int) -> str:
    """Register a user, bypass email verification via DB, log in, return access token."""
    reg = await client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "display_name": "Test User",
        "business_name": f"Test Biz {n}",
        "consent": True,
    })
    assert reg.status_code == 201, reg.text

    # Bypass the email link — mark the user verified directly in the test DB.
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.email_verified = True
    await db_session.commit()

    login = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Register a unique verified user per test and return Bearer auth headers."""
    _counter["n"] += 1
    email = f"user{_counter['n']}@example.com"
    token = await _register_and_verify(client, db_session, email, "testpass123", _counter["n"])
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_client_id(client: AsyncClient, auth_headers: dict) -> str:
    """Create a business client and return its UUID string."""
    resp = await client.post("/api/clients", json={
        "name": "Acme Corp",
        "email": "acme@example.com",
        "phone": "254712000001",
        "address": "Nairobi, Kenya",
    }, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]
