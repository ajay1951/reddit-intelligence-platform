from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_session
from backend.schemas.subreddit import SubredditSchema
from backend.services.subreddit_service import SubredditService

router = APIRouter()


@router.get("/subreddits", response_model=list[SubredditSchema])
async def list_subreddits(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[SubredditSchema]:
    service = SubredditService()
    return await service.list_subreddits(session, limit=limit, offset=offset)
