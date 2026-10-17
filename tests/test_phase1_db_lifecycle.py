import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

import backend.database.connection as db
from backend.etl.tasks import run_subreddit_scrape_task, run_batch_scrape_task


def test_scoped_engine_creation():
    """Verify that create_scoped_engine builds an engine with conservative pool parameters."""
    engine = db.create_scoped_engine(pool_size=4, max_overflow=1)
    assert engine is not None
    assert engine.pool.size() == 4
    assert engine.pool._max_overflow == 1


def test_celery_task_disposes_engine_on_success(monkeypatch):
    """Verify that run_subreddit_scrape_task guarantees engine disposal on success."""
    disposed = []

    class MockAsyncEngine:
        async def dispose(self):
            disposed.append(True)

    mock_engine = MockAsyncEngine()
    monkeypatch.setattr(db, "create_scoped_engine", lambda **kwargs: mock_engine)

    fake_run_etl = AsyncMock(return_value={"status": "success", "posts_scraped": 5})
    monkeypatch.setattr("backend.etl.tasks.run_subreddit_etl", fake_run_etl)

    res = run_subreddit_scrape_task("python", post_limit=5)
    assert res["status"] == "success"
    assert len(disposed) == 1
    assert disposed[0] is True


def test_celery_task_disposes_engine_on_failure(monkeypatch):
    """Verify that run_subreddit_scrape_task guarantees engine disposal even when task raises."""
    disposed = []

    class MockAsyncEngine:
        async def dispose(self):
            disposed.append(True)

    mock_engine = MockAsyncEngine()
    monkeypatch.setattr(db, "create_scoped_engine", lambda **kwargs: mock_engine)

    fake_run_etl = AsyncMock(side_effect=RuntimeError("Transient database disconnect"))
    monkeypatch.setattr("backend.etl.tasks.run_subreddit_etl", fake_run_etl)

    with pytest.raises(RuntimeError, match="Transient database disconnect"):
        run_subreddit_scrape_task("python")

    # Engine must still be disposed via the finally block
    assert len(disposed) == 1
    assert disposed[0] is True


def test_batch_celery_task_disposes_engine(monkeypatch):
    """Verify batch Celery task disposes engine on execution."""
    disposed = []

    class MockAsyncEngine:
        async def dispose(self):
            disposed.append(True)

    mock_engine = MockAsyncEngine()
    monkeypatch.setattr(db, "create_scoped_engine", lambda **kwargs: mock_engine)

    fake_batch_etl = AsyncMock(return_value={"status": "batch_complete", "results": []})
    monkeypatch.setattr("backend.etl.tasks.run_batch_etl", fake_batch_etl)

    res = run_batch_scrape_task(["python", "datascience"])
    assert res["status"] == "batch_complete"
    assert len(disposed) == 1
    assert disposed[0] is True
