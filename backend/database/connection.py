from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

from backend.config import settings

DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)

engine: AsyncEngine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    future=True, 
    poolclass=AsyncAdaptedQueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=1800,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def create_scoped_engine(pool_size: int = 5, max_overflow: int = 2) -> AsyncEngine:
    """Create an isolated AsyncEngine for background worker tasks."""
    return create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=1800,
        pool_pre_ping=True,
    )



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
