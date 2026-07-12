from __future__ import annotations

from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models.models import Comment, Post, Subreddit
from backend.repositories.base import BaseRepository

class CommentRepository(BaseRepository[Comment]):
    """Repository for comment operations."""

    def __init__(self) -> None:
        super().__init__(model=Comment)

    async def get_by_id(self, session: AsyncSession, comment_id: int) -> Optional[Comment]:
        result = await session.execute(select(Comment).where(Comment.id == comment_id))
        return result.scalars().first()

    async def search_comments(self, session: AsyncSession, query: str, limit: int = 5) -> list[Comment]:
        stmt = select(Comment).options(joinedload(Comment.post).joinedload(Post.subreddit)).where(
            text("to_tsvector('english', comments.content) @@ plainto_tsquery('english', :query)")
        ).params(query=query).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def list_comments(self, session: AsyncSession, limit: int = 50, offset: int = 0) -> list[Comment]:
        stmt = select(Comment).order_by(Comment.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())