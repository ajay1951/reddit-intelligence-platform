from __future__ import annotations

import logging
from typing import Any, List, Optional

from apscheduler.jobstores.base import JobLookupError
from fastapi import FastAPI, HTTPException, Request, Depends

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator


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
from backend.api.auth import router as auth_router, get_current_user, require_admin, TokenData
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

import re
import time
import uuid

from backend.api.health import router as health_router
from backend.api.metrics import router as metrics_router, metrics

app = FastAPI(title="reddit-hiring-intel-scraper")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount Routers
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(subreddits_router)
app.include_router(insights_router)
app.include_router(search_router)
app.include_router(stats_router, prefix="/stats")
app.include_router(deep_research_router, prefix="/deep-research")

# Determine and validate CORS origins
parsed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if not parsed_origins:
    parsed_origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=parsed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Admin-Key", "X-Request-ID", "Origin"],
)


@app.middleware("http")
async def correlation_and_metrics_middleware(request: Request, call_next):
    raw_id = request.headers.get("X-Request-ID")
    if raw_id and re.match(r"^[a-zA-Z0-9_\-]{1,64}$", raw_id):
        request_id = raw_id
    else:
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()

    response = await call_next(request)

    duration_ms = (time.time() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    metrics.record_request(request.url.path, response.status_code, duration_ms)

    if not request.url.path.startswith("/health") and not request.url.path.startswith("/metrics"):
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} in {duration_ms:.1f}ms [req_id={request_id}]"
        )
    return response


from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled Server Error: {str(exc)} at {request.url.path} [req_id={req_id}]")
    return JSONResponse(status_code=500, content={"message": "Internal Server Error", "request_id": req_id})


from fastapi.encoders import jsonable_encoder

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation Error: {exc.errors()} at {request.url.path}")
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


class BatchScrapeRequest(BaseModel):
    subreddits: List[str] = Field(..., min_length=1, max_length=100)
    post_limit: int = Field(25, ge=1, le=100000)
    comment_limit: int = Field(5, ge=0, le=100000)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    provider: Optional[str] = Field(None, description="Ingestion provider: 'huggingface', 'apify', or 'auto'")

    @field_validator("subreddits")
    @classmethod
    def validate_subreddits(cls, v: List[str]) -> List[str]:
        cleaned = []
        for s in v:
            s_clean = s.strip()
            if not re.match(r"^[a-zA-Z0-9_]{2,24}$", s_clean):
                raise ValueError(f"Invalid subreddit name '{s}'. Must be alphanumeric/underscores (2-24 chars).")
            cleaned.append(s_clean)
        return cleaned

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_str = v.strip()
            if not v_str:
                return None
            from datetime import datetime
            try:
                datetime.strptime(v_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format '{v}'. Expected YYYY-MM-DD.")
            return v_str
        return None

    @model_validator(mode="after")
    def validate_date_range(self) -> "BatchScrapeRequest":
        if self.start_date and self.end_date:
            from datetime import datetime
            d_start = datetime.strptime(self.start_date, "%Y-%m-%d")
            d_end = datetime.strptime(self.end_date, "%Y-%m-%d")
            if d_start > d_end:
                raise ValueError(f"start_date ({self.start_date}) cannot be after end_date ({self.end_date})")
        return self


class ScheduleRequest(BaseModel):
    job_id: str = Field(..., min_length=1)
    subreddits: List[str] = Field(..., min_length=1)
    post_limit: int = Field(25, ge=1, le=100)
    comment_limit: int = Field(5, ge=0, le=100)
    interval_minutes: int | None = Field(None, ge=1)
    cron: str | None = None
    provider: str | None = None

    @field_validator("subreddits")
    @classmethod
    def validate_subreddits(cls, v: List[str]) -> List[str]:
        cleaned = []
        for s in v:
            s_clean = s.strip()
            if not re.match(r"^[a-zA-Z0-9_]{2,24}$", s_clean):
                raise ValueError(f"Invalid subreddit name '{s}'. Must be alphanumeric/underscores (2-24 chars).")
            cleaned.append(s_clean)
        return cleaned


class DailyHFScheduleRequest(BaseModel):
    subreddits: List[str] = Field(default_factory=lambda: ["MachineLearning", "Python", "LocalLLaMA", "datascience", "technology"])
    post_limit: int = Field(50, ge=1, le=500)
    comment_limit: int = Field(10, ge=0, le=50)
    cron: str = Field("0 0 * * *", description="Cron format: minute hour day-of-month month day-of-week")

    @field_validator("subreddits")
    @classmethod
    def validate_subreddits(cls, v: List[str]) -> List[str]:
        cleaned = []
        for s in v:
            s_clean = s.strip()
            if not re.match(r"^[a-zA-Z0-9_]{2,24}$", s_clean):
                raise ValueError(f"Invalid subreddit name '{s}'. Must be alphanumeric/underscores (2-24 chars).")
            cleaned.append(s_clean)
        return cleaned


@app.on_event("startup")
async def startup_event() -> None:
    if settings.scheduler_enabled:
        try:
            start_scheduler()
            from backend.scheduler import list_scheduled_jobs, schedule_daily_hf_job
            existing_jobs = [j["job_id"] for j in list_scheduled_jobs()]
            if "daily_hf_reddit_sync" not in existing_jobs:
                schedule_daily_hf_job()
                logger.info("Initialized default daily Hugging Face ingestion schedule (0 0 * * *)")
        except Exception as e:
            logger.warning(f"Scheduler failed to start on startup (continuing): {e}")




from backend.etl.tasks import run_batch_scrape_task, run_subreddit_scrape_task

@app.post("/scrape/batch")
async def scrape_batch_endpoint(
    request: BatchScrapeRequest,
    admin_user: TokenData = Depends(require_admin),
) -> dict[str, Any]:
    logger.info(
        "Dispatching batch scrape task to Celery",
        extra={"subreddits": request.subreddits, "provider": request.provider, "requested_by": admin_user.username},
    )
    try:
        task = run_batch_scrape_task.delay(
            request.subreddits,
            post_limit=request.post_limit,
            comment_limit=request.comment_limit,
            concurrency=settings.scraper_concurrency,
            start_date=request.start_date,
            end_date=request.end_date,
            provider=request.provider,
        )
        return {
            "status": "dispatched",
            "task_id": task.id,
            "subreddits": request.subreddits,
            "provider": request.provider or settings.ingestion_provider,
        }
    except Exception as exc:
        logger.exception("batch scrape dispatch failed", extra={"subreddits": request.subreddits})
        raise HTTPException(status_code=500, detail="Batch scrape dispatch failed") from exc

@app.post("/scrape/{subreddit}")
async def scrape_endpoint(
    subreddit: str,
    admin_user: TokenData = Depends(require_admin),
) -> dict[str, Any]:
    subreddit = subreddit.strip()
    if not re.match(r"^[a-zA-Z0-9_]{2,24}$", subreddit):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid subreddit format '{subreddit}'. Must be alphanumeric/underscores (2-24 chars)."
        )
    logger.info("Dispatching scrape task to Celery", extra={"subreddit": subreddit, "requested_by": admin_user.username})
    try:
        task = run_subreddit_scrape_task.delay(subreddit)
        return {"status": "dispatched", "task_id": task.id, "subreddit": subreddit}
    except Exception as exc:
        logger.exception("scrape dispatch failed", extra={"subreddit": subreddit})
        raise HTTPException(status_code=500, detail="Scrape dispatch failed") from exc


@app.post("/schedule")
async def schedule_endpoint(
    request: ScheduleRequest,
    admin_user: TokenData = Depends(require_admin),
) -> dict[str, Any]:
    try:
        result = schedule_etl_job(
            job_id=request.job_id,
            subreddits=request.subreddits,
            post_limit=request.post_limit,
            comment_limit=request.comment_limit,
            interval_minutes=request.interval_minutes,
            cron=request.cron,
            provider=request.provider,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("schedule creation failed", extra={"request": request.dict()})
        raise HTTPException(status_code=500, detail="Scheduling failed") from exc


@app.post("/schedule/daily-hf")
async def schedule_daily_hf_endpoint(
    request: DailyHFScheduleRequest,
    admin_user: TokenData = Depends(require_admin),
) -> dict[str, Any]:
    try:
        from backend.scheduler import schedule_daily_hf_job
        result = schedule_daily_hf_job(
            subreddits=request.subreddits,
            post_limit=request.post_limit,
            comment_limit=request.comment_limit,
            cron=request.cron,
        )
        return {
            "status": "scheduled",
            "provider": "huggingface",
            **result,
        }
    except Exception as exc:
        logger.exception("Failed to schedule daily Hugging Face sync", extra={"request": request.dict()})
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/schedule/jobs")
async def schedule_jobs(
    current_user: TokenData = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return list_scheduled_jobs()


@app.delete("/schedule/jobs/{job_id}")
async def remove_schedule_job(
    job_id: str,
    admin_user: TokenData = Depends(require_admin),
) -> dict[str, Any]:
    try:
        remove_scheduled_job(job_id)
        return {"job_id": job_id, "status": "removed"}
    except JobLookupError:
        raise HTTPException(status_code=404, detail="Scheduled job not found")


@app.get("/schedule/history")
async def schedule_history_endpoint(
    limit: int = 15,
    current_user: TokenData = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Returns audit history of automated 24-hour and on-demand scraping execution runs."""
    from sqlalchemy import select, desc
    from backend.database.connection import AsyncSessionLocal
    from backend.models.models import IngestionRun

    async with AsyncSessionLocal() as session:
        query = select(IngestionRun).order_by(desc(IngestionRun.started_at)).limit(limit)
        res = await session.execute(query)
        runs = res.scalars().all()
        return [
            {
                "id": r.id,
                "job_id": r.job_id,
                "status": r.status,
                "subreddits": r.subreddits,
                "posts_ingested": r.posts_ingested,
                "comments_ingested": r.comments_ingested,
                "provider_used": r.provider_used,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error_message": r.error_message,
            }
            for r in runs
        ]



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.scripts.run_scraper:app",
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level.lower(),
    )
