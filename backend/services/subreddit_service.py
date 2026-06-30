from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.subreddit_repository import SubredditRepository
from backend.schemas.subreddit import SubredditSchema


class SubredditService:
    def __init__(self, repository: SubredditRepository | None = None) -> None:
        self.repository = repository or SubredditRepository()

    async def list_subreddits(
        self,
        session: AsyncSession,
        limit: int = 25,
        offset: int = 0,
    ) -> list[SubredditSchema]:
        results = await self.repository.list_subreddits(session, limit=limit, offset=offset)
        return [
            SubredditSchema(
                id=subreddit.id,
                name=subreddit.name,
                url=subreddit.url,
                created_at=subreddit.created_at,
                post_count=post_count,
            )
            for subreddit, post_count in results
        ]
