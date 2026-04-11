from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import get_settings

_settings = get_settings()

_engine_kwargs: dict[str, Any] = {"echo": False, "pool_pre_ping": True}
if _settings.database_use_null_pool:
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(_settings.database_url, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
