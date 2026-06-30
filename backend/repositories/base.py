from __future__ import annotations

from typing import Generic, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic repository for basic CRUD operations.

    This is intentionally minimal; specialized repositories extend it.
    """

    def __init__(self, model: Type[T]):
        self.model = model

    async def add(self, session: AsyncSession, instance: T) -> T:
        session.add(instance)
        await session.flush()
        return instance
