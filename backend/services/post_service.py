from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.post_repository import PostRepository
from backend.schemas.post import PostSchema


class PostService:
    def __init__(self, repository: PostRepository | None = None) -> None:
        self.repository = repository or PostRepository()

    async def list_posts(
        self,
        session: AsyncSession,
        limit: int = 25,
        offset: int = 0,
        subreddit: str | None = None,
    ) -> list[PostSchema]:
        posts = await self.repository.list_posts(
            session,
            limit=limit,
            offset=offset,
            subreddit_name=subreddit,
        )
        return [self._to_schema(post) for post in posts]

    def _to_schema(self, post) -> PostSchema:
        return PostSchema(
            id=post.id,
            title=post.title,
            author=post.author,
            subreddit=post.subreddit.name if post.subreddit is not None else "",
            score=post.score,
            comments_count=post.comments_count,
            url=post.url,
            content=post.content,
            created_at=post.created_at,
            scraped_at=post.scraped_at,
        )
