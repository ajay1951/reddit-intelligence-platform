from typing import Any, Dict, List

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import crud, models
from services.job_requirement_extractor import JobRequirementExtractor
from services.salary_extractor import SalaryExtractor
from services.skill_extractor import SkillExtractor
from services.trend_analyzer import TrendAnalyzer

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """
    Service to orchestrate data extraction, analysis, and storage.
    Also provides data for the analytics API.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.skill_extractor = SkillExtractor()
        self.salary_extractor = SalaryExtractor()
        self.job_req_extractor = JobRequirementExtractor()
        self.trend_analyzer = TrendAnalyzer(db_session)
        logger.info("AnalyticsService initialized.")

    async def process_reddit_post(
        self, post: models.Post, comments: List[models.Comment]
    ):
        """
        Processes a single Reddit post and its comments to extract intelligence.
        This is the main entry point for the intelligence engine pipeline.
        """
        logger.info("Processing post", post_id=post.id, num_comments=len(comments))

        # Combine text from post and all comments for skill and salary analysis
        full_text = post.t
        if job_details:
            await crud.create_job_requirement(self.db, job_details, post.id)

        logger.info("Finished processing post", post_id=post.id)

    # --- Methods for Analytics API ---

    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Provides a summary for the main dashboard."""
        total_posts = await self.db.scalar(select(func.count(models.Post.id)))
        total_comments = await self.db.scalar(select(func.count(models.Comment.id)))
        total_skills = await self.db.scalar(select(func.count(models.Skill.id)))

        avg_salary_res = await self.db.execute(
            select(func.avg(models.SalaryMention.amount_min)).where(
                models.SalaryMention.currency == "USD"
            )
        )
        avg_salary = avg_salary_res.scalar_one_or_none() or 0

        top_role_res = await self.db.execute(
            select(
                models.JobRequirement.role_title,
                func.count(models.JobRequirement.id).label("count"),
            )
            .group_by(models.JobRequirement.role_title)
            .order_by(func.count(models.JobRequirement.id).desc())
            .limit(1)
        )
        top_role = top_role_res.first()

        return {
            "total_posts": total_posts,
            "total_comments": total_comments,
            "total_skills_tracked": total_skills,
            "average_salary_usd": round(avg_salary, 2),
            "top_job_role": top_role.role_title if top_role else "N/A",
        }

    async def get_top_skills(self, limit: int = 20) -> List[models.Skill]:
        return await crud.get_top_skills(self.db, limit)

    # ... other analytics methods will be added in Phase 6 ...