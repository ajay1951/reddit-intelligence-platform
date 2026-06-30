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
from backend.routers import (
    comments_router,
    insights_router,
    posts_router,
    search_router,
    subreddits_router,
)
from backend.routers.stats import router as stats_router
from backend.scheduler import (
    get_scheduler,
    list_scheduled_jobs,
    remove_scheduled_job,
    schedule_etl_job,
    start_scheduler,
)

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title="reddit-hiring-intel-scraper")
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(subreddits_router)
app.include_router(insights_router)
app.include_router(search_router)
app.include_router(stats_router, prefix="/stats")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BatchScrapeRequest(BaseModel):
    subreddits: List[str] = Field(..., min_item
        return result
    except Exception as exc:
        logger.exception("batch scrape failed", extra={"subreddits": request.subreddits})
        raise HTTPException(status_code=500, detail="Batch scrape failed") from exc


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
