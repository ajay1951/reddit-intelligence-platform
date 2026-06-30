from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.analytics_service import AnalyticsService

logger = structlog.get_logger(__name__)
router = APIRouter()


# --- Pydantic Response Models ---


class SkillResponse(BaseModel):
    id: int
    skill_name: str
    mention_count: int
    last_updated: datetime

    class Config:
        orm_mode = True


class SkillTrendResponse(BaseModel):
    skill_name: str
    date: datetime
    mentions: int
    daily_growth: float

    class Config:
        orm_mode = True


class SkillDetailResponse(BaseModel):
    details: SkillResponse
    trends: List[SkillTrendResponse]


class SalaryInsightsResponse(BaseModel):
    average_yearly_usd: float
    min_yearly_usd: float
    max_yearly_usd: float
    mention_count: int


class JobRequirementResponse(BaseModel):
    id: int
    role_title: Optional[str]
    experience_years: Optional[int]
    required_skills: Optional[List[str]]
    preferred_skills: Optional[List[str]]
    location: Optional[str]
    work_model: Optional[str]
    salary_min: Optional[float]
    salary_max: Optional[float]
    salary_currency: Optional[str]
    source_post_id: str

    class Config:
        orm_mode = True


class DashboardSummaryResponse(BaseModel):
    total_posts: int
    total_comments: int
    total_skills_tracked: int
    average_salary_usd: float
    top_job_role: str


# --- API Endpoints ---


def get_analytics_service(
    db: AsyncSession = Depends(get_db),
) -> AnalyticsService:
    return AnalyticsService(db)


@router.get(
    "/dashboard",
    response_model=DashboardSummaryResponse,
    summary="Get Dashboard Summary",
)
async def get_dashboard(
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Provides a high-level summary for the main dashboard."""
    return await service.get_dashboard_summary()


@router.get(
    "/top-skills", response_model=List[SkillResponse], summary="Get Top Mentioned Skills"
)
async def get_top_skills(
    limit: int = 20, service: AnalyticsService = Depends(get_analytics_service)
):
    """Retrieves a list of the most mentioned skills."""
    return await service.get_top_skills(limit)


@router.get(
    "/trending-skills",
    response_model=List[SkillTrendResponse],
    summary="Get Trending Skills",
)
async def get_trending_skills(
    limit: int = 10, service: AnalyticsService = Depends(get_analytics_service)
):
    """Retrieves a list of skills with the highest daily growth."""
    return await service.get_trending_skills(limit)


@router.get(
    "/salary-insights",
    response_model=SalaryInsightsResponse,
    summary="Get Salary Insights",
)
async def get_salary_insights(
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Provides insights into salary data extracted from posts."""
    return await service.get_salary_insights()


@router.get(
    "/job-requirements",
    response_model=List[JobRequirementResponse],
    summary="Get Job Requirements",
)
async def get_job_requirements(
    skip: int = 0,
    limit: int = 20,
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Retrieves a paginated list of extracted job requirements."""
    return await service.get_job_requirements_list(skip, limit)


@router.get(
    "/skill/{skill_name}",
    response_model=SkillDetailResponse,
    summary="Get Details for a Specific Skill",
)
async def get_skill_details(
    skill_name: str, service: AnalyticsService = Depends(get_analytics_service)
):
    """Fetches mention counts and trend history for a specific skill."""
    details = await service.get_skill_by_name(skill_name)
    if not details:
        raise HTTPException(status_code=404, detail="Skill not found")
    return details


@router.get("/roles", response_model=List[str], summary="Get Unique Job Roles")
async def get_roles(service: AnalyticsService = Depends(get_analytics_service)):
    """Retrieves a list of unique job roles found in job postings."""
    return await service.get_unique_roles()


@router.get(
    "/market-summary",
    response_model=DashboardSummaryResponse,
    summary="Get Market Summary",
)
async def get_market_summary(service: AnalyticsService = Depends(get_analytics_service)):
    """Provides a high-level summary of the job market data."""
    return await service.get_market_summary()