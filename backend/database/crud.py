from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from . import models
from ..services.job_requirement_extractor import ExtractedJob

logger = structlog.get_logger(__name__)


async def bulk_upsert_skills(db: AsyncSession, skill_counts: Dict[str, int]):
    """
    Atomically increments mention counts for a batch of skills.
    Inserts new skills if they don't exist.
    """
    if not skill_counts:
        return

    insert_stmt = insert(models.Skill).values(
        [
            {"skill_name": name, "mention_count": count}
            for name, count in skill_counts.items()
        ]
    )

    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["skill_name"],
        set_=dict(
            mention_count=models.Skill.mention_count + insert_stmt.excluded.mention_count
        )
    )
    await db.execute(upsert_stmt)

    await db.commit()
    logger.info("Bulk upserted skills", count=len(skill_counts))


async def create_salary_mentions(
    db: AsyncSession, salaries: List[Dict[str, Any]], post_id: str
):
    """Creates multiple salary mention records in the database."""
    if not salaries:
        return

    db.add_all(
        [
            models.SalaryMention(
                currency=s["currency"],
                amount_min=s["amount_min"],
                amount_max=s.get("amount_max"),
                period=s["period"],
                source_post_id=post_id,
            )
            for s in salaries
        ]
    )
    await db.commit()
    logger.info("Created salary mentions", count=len(salaries), post_id=post_id)


async def create_job_requirement(
    db: AsyncSession, job_details: ExtractedJob, post_id: str
):
    """Creates a job requirement record in the database."""
    job_req = models.JobRequirement(
        role_title=job_details.role_title,
        experience_years=job_details.experience_years,
        required_skills=job_details.required_skills,
        preferred_skills=job_details.preferred_skills,
        location=job_details.location,
        work_model=job_details.work_model,
        salary_min=job_details.salary_min,
        salary_max=job_details.salary_max,
        salary_currency=job_details.salary_currency,
        source_post_id=post_id,
    )
    db.add(job_req)
    await db.commit()
    logger.info("Created job requirement", post_id=post_id, role=job_details.role_title)


# --- CRUD for Analytics API ---


async def get_top_skills(db: AsyncSession, limit: int = 20) -> List[models.Skill]:
    """Retrieves the top N skills by mention count."""
    result = await db.execute(
        select(models.Skill).order_by(desc(models.Skill.mention_count)).limit(limit)
    )
    return result.scalars().all()


async def get_trending_skills(
    db: AsyncSession, limit: int = 10
) -> List[models.SkillTrend]:
    """Retrieves the top N trending skills based on daily growth."""
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    result = await db.execute(
        select(models.SkillTrend)
        .where(func.date(models.SkillTrend.date) == yesterday)
        .order_by(desc(models.SkillTrend.daily_growth))
        .limit(limit)
    )
    return result.scalars().all()


async def get_salary_insights(db: AsyncSession) -> Dict[str, Any]:
    """Retrieves salary statistics, focusing on yearly USD for simplicity."""
    query = select(
        func.avg(models.SalaryMention.amount_min),
        func.min(models.SalaryMention.amount_min),
        func.max(models.SalaryMention.amount_min),
        func.count(models.SalaryMention.id),
    ).where(
        models.SalaryMention.currency == "USD", models.SalaryMention.period == "yearly"
    )
    result = await db.execute(query)
    avg, min_sal, max_sal, count = result.one()

    return {
        "average_yearly_usd": round(avg, 2) if avg else 0,
        "min_yearly_usd": min_sal or 0,
        "max_yearly_usd": max_sal or 0,
        "mention_count": count or 0,
    }


async def get_job_requirements(
    db: AsyncSession, skip: int = 0, limit: int = 20
) -> List[models.JobRequirement]:
    """Retrieves a list of job requirements with pagination."""
    result = await db.execute(
        select(models.JobRequirement)
        .order_by(desc(models.JobRequirement.created_at))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_skill_details(
    db: AsyncSession, skill_name: str
) -> Optional[models.Skill]:
    """Retrieves details for a specific skill."""
    result = await db.execute(
        select(models.Skill).where(models.Skill.skill_name.ilike(skill_name))
    )
    return result.scalars().first()


async def get_skill_trend_history(
    db: AsyncSession, skill_name: str, days: int = 30
) -> List[models.SkillTrend]:
    """Retrieves the trend history for a specific skill."""
    start_date = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(models.SkillTrend)
        .where(
            models.SkillTrend.skill_name.ilike(skill_name),
            models.SkillTrend.date >= start_date,
        )
        .order_by(models.SkillTrend.date)
    )
    return result.scalars().all()


async def get_unique_roles(db: AsyncSession, limit: int = 50) -> List[str]:
    """Retrieves a list of unique job roles."""
    result = await db.execute(
        select(models.JobRequirement.role_title)
        .distinct()
        .order_by(models.JobRequirement.role_title)
        .limit(limit)
    )
    return result.scalars().all()
