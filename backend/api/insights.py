from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_session
from backend.schemas.insight import SkillSchema, TrendResponse
from backend.services.insight_service import InsightService

router = APIRouter()


@router.get("/skills", response_model=list[SkillSchema])
async def get_skills(
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[SkillSchema]:
    service = InsightService()
    return await service.get_skills(session, limit=limit)


@router.get("/trends", response_model=TrendResponse)
async def get_trends(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> TrendResponse:
    service = InsightService()
    return await service.get_trends(session, limit=limit)
