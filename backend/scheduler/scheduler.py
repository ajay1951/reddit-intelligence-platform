from __future__ import annotations

import logging
from typing import Any

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import settings
from backend.etl.pipeline import run_batch_etl

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None


def _build_jobstore_url() -> str:
    if settings.scheduler_job_store_url:
        return settings.scheduler_job_store_url

    return (
        f"postgresql+psycopg://{settings.postgres_user}:"
        f"{settings.postgres_password}@{settings.postgres_host}:"
        f"{settings.postgres_port}/{settings.postgres_db}"
    )


def get_scheduler() -> AsyncIOScheduler:
    global scheduler
    if scheduler is None:
        jobstores = {"default": SQLAlchemyJobStore(url=_build_jobstore_url())}
        scheduler = AsyncIOScheduler(jobstores=jobstores, job_defaults={"coalesce": False, "max_instances": 1})
    return scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("ETL scheduler started")


def shutdown_scheduler() -> None:
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("ETL scheduler stopped")


def schedule_etl_job(
    job_id: str,
    subreddits: list[str],
    post_limit: int = 25,
    comment_limit: int = 5,
    interval_minutes: int | None = None,
    cron: str | None = None,
) -> dict[str, Any]:
    scheduler = get_scheduler()
    trigger = None

    if cron:
        trigger = CronTrigger.from_crontab(cron)
    elif interval_minutes is not None:
        trigger = IntervalTrigger(minutes=interval_minutes)
    else:
        raise ValueError("Either interval_minutes or cron must be set.")

    def sync_run_batch_etl(subs, p_lim, c_lim, conc):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_batch_etl(subs, p_lim, c_lim, conc))
        finally:
            loop.close()

    scheduler.add_job(
        sync_run_batch_etl,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        args=[subreddits, post_limit, comment_limit, settings.scraper_concurrency]
    )

    job = scheduler.get_job(job_id)
    return {
        "job_id": job_id,
        "next_run_time": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "trigger": type(trigger).__name__,
    }


def list_scheduled_jobs() -> list[dict[str, Any]]:
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()
    return [
        {
            "job_id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": type(job.trigger).__name__,
        }
        for job in jobs
    ]


def remove_scheduled_job(job_id: str) -> None:
    scheduler = get_scheduler()
    scheduler.remove_job(job_id)
