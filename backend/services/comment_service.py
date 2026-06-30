from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.comment_repository import CommentRepository
from backend.schemas.comment import CommentSchema


class CommentService:
    def __init__(self, repository: CommentRepository | None = None) -> None:
        self.repository = repository or CommentRepository()

    async def list_comments(
        self,
        session: AsyncSession,
        limit: int = 25,
        offset: int = 0,
        post_id: int | None = None,
        subreddit: str | None = None,
    ) -> list[CommentSchema]:
        comments = await self.repository.list_comments(
            session,
            limit=limit,
            offset=offset,
            post_id=post_id,
            subreddit_name=subreddit,
        )
        return [self._to_schema(comment) for comment in comments]

    def _to_schema(self, comment) -> CommentSchema:
        return CommentSchema(
            id=comment.id,
            post_id=comment.post_id,
            post_url=comment.post.url if comment.post is not None else None,
            subreddit=comment.post.subreddit.name if comment.post is not None and comment.post.subreddit is not None else None,
            author=comment.author,
            content=comment.content,
            score=comment.score,
            created_at=comment.created_at,
        )
