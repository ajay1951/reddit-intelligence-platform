from __future__ import annotations

import pickle
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.etl.tasks import run_batch_scrape_task
from backend.scheduler.scheduler import dispatch_scheduled_batch_etl


def test_scheduler_dispatcher_is_picklable():
    """Verify that the scheduled dispatcher function can be serialized by SQLAlchemyJobStore."""
    pickled = pickle.dumps(dispatch_scheduled_batch_etl)
    assert pickled is not None
    unpickled = pickle.loads(pickled)
    assert unpickled == dispatch_scheduled_batch_etl
    assert unpickled.__name__ == "dispatch_scheduled_batch_etl"


def test_scheduler_dispatcher_invokes_celery():
    with patch("backend.etl.tasks.run_batch_scrape_task.delay") as mock_delay:
        dispatch_scheduled_batch_etl(["technology"])
        mock_delay.assert_called_once()


def test_celery_task_configuration():
    """Verify Celery task attributes for production reliability."""
    assert run_batch_scrape_task.acks_late is True
    assert run_batch_scrape_task.max_retries == 3
    assert run_batch_scrape_task.default_retry_delay == 60


from celery.exceptions import Retry


def test_celery_task_retries_on_failure(monkeypatch):
    """Verify task catches unexpected exceptions and triggers bounded exponential retry."""
    fake_batch_etl = AsyncMock(side_effect=RuntimeError("ETL transient failure"))
    monkeypatch.setattr("backend.etl.tasks.run_batch_etl", fake_batch_etl)

    mock_retry = MagicMock(side_effect=Retry("RetryTriggered"))
    monkeypatch.setattr(run_batch_scrape_task, "retry", mock_retry)

    with pytest.raises(Retry):
        run_batch_scrape_task(["technology"])

    mock_retry.assert_called_once()
    _, kwargs = mock_retry.call_args
    assert kwargs["countdown"] == 60  # 60 * (2 ** 0) = 60


def test_scheduler_dispatcher_passes_provider():
    """Verify that dispatch_scheduled_batch_etl forwards provider parameter to Celery delay."""
    with patch("backend.etl.tasks.run_batch_scrape_task.delay") as mock_delay:
        dispatch_scheduled_batch_etl(
            ["MachineLearning", "Python"],
            post_limit=50,
            comment_limit=10,
            provider="huggingface",
        )
        mock_delay.assert_called_once_with(
            subreddits=["MachineLearning", "Python"],
            post_limit=50,
            comment_limit=10,
            concurrency=1,
            provider="huggingface",
        )


def test_schedule_daily_hf_job():
    """Verify daily Hugging Face cron configuration."""
    from backend.scheduler.scheduler import schedule_daily_hf_job, list_scheduled_jobs, remove_scheduled_job
    
    res = schedule_daily_hf_job(
        subreddits=["Python", "datascience"],
        post_limit=30,
        comment_limit=8,
        cron="0 2 * * *",
    )
    assert res["job_id"] == "daily_hf_reddit_sync"
    assert res["provider"] == "huggingface"
    assert res["trigger"] == "CronTrigger"
    assert res["subreddits"] == ["Python", "datascience"]

    jobs = list_scheduled_jobs()
    daily_job = next((j for j in jobs if j["job_id"] == "daily_hf_reddit_sync"), None)
    assert daily_job is not None
    assert daily_job["provider"] == "huggingface"

    remove_scheduled_job("daily_hf_reddit_sync")


def test_celery_beat_24h_schedule():
    """Verify Celery Beat 24-hour autonomous schedule registration."""
    from backend.celery_app import celery_app
    schedule = celery_app.conf.beat_schedule
    assert "daily-autonomous-reddit-scrape" in schedule
    entry = schedule["daily-autonomous-reddit-scrape"]
    assert entry["task"] == "backend.etl.tasks.run_batch_scrape_task"
    assert entry["kwargs"]["provider"] == "auto"


