from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_session
from backend.schemas.comment import CommentSchema
from backend.services.comment_service import CommentService

router = APIRouter()


@router.get("/comments", response_model=list[CommentSchema])
async def list_comments(
    post_id: int | None = Query(None, ge=1),
    subreddit: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[CommentSchema]:
    service = CommentService()
    return await service.list_comments(
        session,
        limit=limit,
        offset=offset,
        post_id=post_id,
        subreddit=subreddit,
    )
