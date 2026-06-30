from __future__ import annotations

from typing import Optional

from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models.models import Post, Subreddit
from backend.repositories.base import BaseRepository


class PostRepository(BaseRepository[Post]):
    """Repository for post operations."""

    def __init__(self) -> None:
        super().__init__(Post)

    async def get_by_url(self, session: AsyncSession, url: str) -> Optional[Post]:
        stmt = select(Post).where(Post.url == url)
        resp = await session.execute(stmt)
        return resp.scalars().first()

    async def create_post(
        self,
        session: AsyncSession,
        title: str,
        author: str | None,
        subreddit: Subreddit,
        score: int,
        comments_count: int,
        url: str,
        content: str | None,
        created_at,
    ) -> Post:
        post = Post(
            title=title,
            author=author,
            subreddit=subreddit,
            score=score,
            comments_count=comments_count,
            url=url,
            content=content,
            created_at=created_at,
        )
        await self.add(session, post)
        return post

    async def list_posts(
        self,
        session: AsyncSession,
        limit: int = 25,
        offset: int = 0,
        subreddit_name: str | None = None,
    ) -> list[Post]:
        stmt = select(Post).options(joinedload(Post.subreddit)).order_by(desc(Post.created_at))
        if subreddit_name:
            stmt = stmt.join(Post.subreddit).where(Subreddit.name == subreddit_name)
        stmt = stmt.limit(limit).offset(offset)
        resp = await session.execute(stmt)
        return resp.scalars().all()

    async def search_posts(self, session: AsyncSession, query: str, limit: int = 5) -> list[Post]:
        stmt = select(Post).options(joinedload(Post.subreddit)).where(
            text("to_tsvector('english', title || ' ' || coalesce(content, '')) @@ plainto_tsquery('english', :query)")
        ).params(query=query).limit(limit)
        resp = await session.execute(stmt)
        return list(resp.scalars().all())
