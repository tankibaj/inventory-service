"""
Test configuration and shared fixtures.

Database strategy:
- Use a real PostgreSQL DB (started via docker-compose before tests run)
- DATABASE_USE_NULL_POOL=true disables connection pooling — avoids asyncpg event-loop conflicts
- Each test truncates tables before running (fast, clean isolation)
- Function-scoped fixtures throughout
"""

import os
import uuid
from collections.abc import AsyncGenerator

# Set NullPool BEFORE importing src modules so the engine is created with NullPool
os.environ.setdefault("DATABASE_USE_NULL_POOL", "true")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://inventory:inventory@localhost:5432/inventory",
)
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://inventory:inventory@localhost:5432/inventory",
)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return TENANT_ID


@pytest.fixture
async def app():
    """App fixture — uses the module-level engine (NullPool-configured via env)."""
    from src.main import create_app

    application = create_app()
    yield application


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Function-scoped httpx async client for API tests."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
async def clean_db() -> AsyncGenerator[None, None]:
    """
    Truncate all tables BEFORE each test so each test starts with a clean state.
    NullPool ensures connections don't linger across tests.
    """
    from src.database import async_session_factory

    async with async_session_factory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE stock_reservations, stock_levels, skus, products "
                "RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
    yield
