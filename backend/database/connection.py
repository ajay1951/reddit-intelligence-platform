from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from backend.config import settings


DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)


engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True, poolclass=NullPool)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_session_context() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_session() -> AsyncIterator[AsyncSession]:
    """Async generator dependency that yields DB sessions."""
    async with AsyncSessionLocal() as session:
        yield session


def run_migrations() -> None:
    """Placeholder to run migrations programmatically if needed."""
    # Alembic is configured separately. Keep placeholder for future automation.
    pass
