"""Async DB engine helpers.

The engine and session factory live on app.state (set in lifespan),
not in module globals, so tests can inject a different database URL
without monkeypatching.

Usage in routes:
    async def my_route(db: AsyncSession = Depends(get_db)): ...

Usage in tests:
    app.state.session_factory = async_sessionmaker(test_engine, ...)
"""

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        pool_size=10,
        pool_timeout=10,
        echo=settings.debug,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a session from app.state.session_factory."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session
