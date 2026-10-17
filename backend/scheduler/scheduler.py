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
    is_loop_dead = False
    if scheduler is not None:
        loop = getattr(scheduler, "_eventloop", None)
        if loop is not None and hasattr(loop, "is_closed"):
            try:
                is_loop_dead = loop.is_closed()
            except Exception:
                is_loop_dead = True

    if scheduler is None or is_loop_dead:
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


def dispatch_scheduled_batch_etl(
    subreddits: list[str],
    post_limit: int = 25,
    comment_limit: int = 5,
    concurrency: int = 1,
    provider: str | None = None,
) -> str:
    """
    Top-level picklable entrypoint for APScheduler persistent jobstore.
    Delegates background execution to Celery instead of running heavy jobs
    synchronously inside the scheduler event loop.
    """
    from backend.etl.tasks import run_batch_scrape_task

    task = run_batch_scrape_task.delay(
        subreddits=subreddits,
        post_limit=post_limit,
        comment_limit=comment_limit,
        concurrency=concurrency,
        provider=provider,
    )
    logger.info("Dispatched scheduled batch ETL task to Celery", task_id=task.id, subreddits=subreddits, provider=provider)
    return task.id


def schedule_etl_job(
    job_id: str,
    subreddits: list[str],
    post_limit: int = 25,
    comment_limit: int = 5,
    interval_minutes: int | None = None,
    cron: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    scheduler = get_scheduler()
    trigger = None

    if cron:
        trigger = CronTrigger.from_crontab(cron)
    elif interval_minutes is not None:
        trigger = IntervalTrigger(minutes=interval_minutes)
    else:
        raise ValueError("Either interval_minutes or cron must be set.")

    scheduler.add_job(
        dispatch_scheduled_batch_etl,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        args=[subreddits, post_limit, comment_limit, settings.scraper_concurrency, provider],
    )

    job = scheduler.get_job(job_id)
    next_run = getattr(job, "next_run_time", None)
    if next_run is None and trigger:
        from datetime import datetime, timezone
        try:
            next_run = trigger.get_next_fire_time(None, datetime.now(timezone.utc))
        except Exception:
            next_run = None

    return {
        "job_id": job_id,
        "next_run_time": next_run.isoformat() if next_run else None,
        "trigger": type(trigger).__name__,
        "provider": provider or settings.ingestion_provider,
        "subreddits": subreddits,
    }


def schedule_daily_hf_job(
    subreddits: list[str] | None = None,
    post_limit: int = 50,
    comment_limit: int = 10,
    cron: str = "0 0 * * *",
) -> dict[str, Any]:
    """
    Registers or updates the persistent daily Hugging Face automated ingestion job.
    Runs zero-cost DuckDB streaming at midnight UTC (or custom cron expression).
    """
    target_subs = subreddits or ["technology", "MachineLearning", "Python", "LocalLLaMA", "datascience"]
    return schedule_etl_job(
        job_id="daily_hf_reddit_sync",
        subreddits=target_subs,
        post_limit=post_limit,
        comment_limit=comment_limit,
        cron=cron,
        provider="huggingface",
    )


def list_scheduled_jobs() -> list[dict[str, Any]]:
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()
    result = []
    for job in jobs:
        next_run = getattr(job, "next_run_time", None)
        if next_run is None and getattr(job, "trigger", None):
            from datetime import datetime, timezone
            try:
                next_run = job.trigger.get_next_fire_time(None, datetime.now(timezone.utc))
            except Exception:
                next_run = None

        job_info: dict[str, Any] = {
            "job_id": job.id,
            "next_run_time": next_run.isoformat() if next_run else None,
            "trigger": type(job.trigger).__name__ if getattr(job, "trigger", None) else "Unknown",
        }
        if getattr(job, "args", None):
            if len(job.args) > 0 and isinstance(job.args[0], list):
                job_info["subreddits"] = job.args[0]
            if len(job.args) > 1 and isinstance(job.args[1], int):
                job_info["post_limit"] = job.args[1]
            if len(job.args) > 2 and isinstance(job.args[2], int):
                job_info["comment_limit"] = job.args[2]
            if len(job.args) > 4:
                job_info["provider"] = job.args[4] or "auto"
        result.append(job_info)
    return result


def remove_scheduled_job(job_id: str) -> None:
    scheduler = get_scheduler()
    scheduler.remove_job(job_id)
