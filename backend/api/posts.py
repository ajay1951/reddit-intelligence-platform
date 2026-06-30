from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_session
from backend.schemas.post import PostSchema
from backend.services.post_service import PostService

router = APIRouter()


@router.get("/posts", response_model=list[PostSchema])
async def list_posts(
    subreddit: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[PostSchema]:
    service = PostService()
    return await service.list_posts(session, limit=limit, offset=offset, subreddit=subreddit)
