import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "backend",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.etl.tasks"]
)

from celery.schedules import crontab

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "daily-autonomous-reddit-scrape": {
            "task": "backend.etl.tasks.run_batch_scrape_task",
            "schedule": crontab(hour=0, minute=0),  # Every 24 hours at 00:00 UTC
            "args": (["MachineLearning", "Python", "LocalLLaMA", "datascience", "technology"], 50, 10),
            "kwargs": {"provider": "auto"},
        }
    },
)

