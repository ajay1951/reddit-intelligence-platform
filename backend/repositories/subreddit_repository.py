from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import Subreddit

class SubredditRepository:
    async def get_by_name(self, session: AsyncSession, name: str) -> Subreddit | None:
        stmt = select(Subreddit).where(Subreddit.name == name)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_all(self, session: AsyncSession) -> list[Subreddit]:
        stmt = select(Subreddit)
        result = await session.execute(stmt)
        return list(result.scalars().all())
