from __future__ import annotations

import logging
from typing import Any, List

from apscheduler.jobstores.base import JobLookupError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import settings
from backend.etl.pipeline import run_batch_etl, run_subreddit_etl
from backend.logging_config import configure_logging
from backend.api import (
    comments_router,
    insights_router,
    posts_router,
    search_router,
    subreddits_router,
    deep_research_router,
)
from backend.api.stats import router as stats_router
from backend.scheduler import (
    get_scheduler,
    list_scheduled_jobs,
    remove_scheduled_job,
    schedule_etl_job,
    start_scheduler,
)

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.api.limiter import limiter

app = FastAPI(title="reddit-hiring-intel-scraper")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(subreddits_router)
app.include_router(insights_router)
app.include_router(search_router)
app.include_router(stats_router, prefix="/stats")
app.include_router(deep_research_router, prefix="/deep-research")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.exception("Unhandled Server Error", error=str(exc), path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    logger.warning("Validation Error", errors=exc.errors(), path=request.url.path)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


class BatchScrapeRequest(BaseModel):
    subreddits: List[str] = Field(..., min_items=1)
    post_limit: int = Field(25, ge=1, le=10000)
    comment_limit: int = Field(5, ge=0, le=100)


class ScheduleRequest(BaseModel):
    job_id: str = Field(..., min_length=1)
    subreddits: List[str] = Field(..., min_items=1)
    post_limit: int = Field(25, ge=1, le=100)
    comment_limit: int = Field(5, ge=0, le=100)
    interval_minutes: int | None = Field(None, ge=1)
    cron: str | None = None


@app.on_event("startup")
async def startup_event() -> None:
    if settings.scheduler_enabled:
        start_scheduler()


@app.get("/health")
async def health() -> dict[str, Any]:
    scheduler = get_scheduler() if settings.scheduler_enabled else None
    return {
        "status": "ok",
        "scheduler_enabled": settings.scheduler_enabled,
        "scheduler_running": scheduler.running if scheduler else False,
    }


from backend.etl.tasks import run_batch_scrape_task, run_subreddit_scrape_task

@app.post("/scrape/batch")
async def scrape_batch_endpoint(request: BatchScrapeRequest) -> dict[str, Any]:
    logger.info("Dispatching batch scrape task to Celery", extra={"subreddits": request.subreddits})
    try:
        task = run_batch_scrape_task.delay(
            request.subreddits,
            post_limit=request.post_limit,
            comment_limit=request.comment_limit,
            concurrency=settings.scraper_concurrency,
        )
        return {"status": "dispatched", "task_id": task.id, "subreddits": request.subreddits}
    except Exception as exc:
        logger.exception("batch scrape dispatch failed", extra={"subreddits": request.subreddits})
        raise HTTPException(status_code=500, detail="Batch scrape dispatch failed") from exc

@app.post("/scrape/{subreddit}")
async def scrape_endpoint(subreddit: str) -> dict[str, Any]:
    logger.info("Dispatching scrape task to Celery", extra={"subreddit": subreddit})
    try:
        task = run_subreddit_scrape_task.delay(subreddit)
        return {"status": "dispatched", "task_id": task.id, "subreddit": subreddit}
    except Exception as exc:
        logger.exception("scrape dispatch failed", extra={"subreddit": subreddit})
        raise HTTPException(status_code=500, detail="Scrape dispatch failed") from exc


@app.post("/schedule")
async def schedule_endpoint(request: ScheduleRequest) -> dict[str, Any]:
    try:
        result = schedule_etl_job(
            job_id=request.job_id,
            subreddits=request.subreddits,
            post_limit=request.post_limit,
            comment_limit=request.comment_limit,
            interval_minutes=request.interval_minutes,
            cron=request.cron,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("schedule creation failed", extra={"request": request.dict()})
        raise HTTPException(status_code=500, detail="Scheduling failed") from exc


@app.get("/schedule/jobs")
async def schedule_jobs() -> list[dict[str, Any]]:
    return list_scheduled_jobs()


@app.delete("/schedule/jobs/{job_id}")
async def remove_schedule_job(job_id: str) -> dict[str, Any]:
    try:
        remove_scheduled_job(job_id)
        return {"job_id": job_id, "status": "removed"}
    except JobLookupError:
        raise HTTPException(status_code=404, detail="Scheduled job not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.scripts.run_scraper:app",
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level.lower(),
    )
