import asyncio
from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.future import select

from backend.models.models import Base, Subreddit, Post, Comment
from backend.etl.pipeline import _make_comment_id, parse_iso_datetime, run_subreddit_etl
from backend.config import settings
from backend.api.main import BatchScrapeRequest


def test_batch_scrape_request_date_validation():
    """Verify that BatchScrapeRequest enforces YYYY-MM-DD format and valid range."""
    # 1. Valid dates
    req = BatchScrapeRequest(
        subreddits=["python"],
        start_date="2026-01-01",
        end_date="2026-01-31"
    )
    assert req.start_date == "2026-01-01"
    assert req.end_date == "2026-01-31"

    # 2. Invalid date format
    with pytest.raises(ValueError, match="Invalid date format"):
        BatchScrapeRequest(
            subreddits=["python"],
            start_date="01-31-2026"
        )

    # 3. start_date > end_date
    with pytest.raises(ValueError, match="cannot be after end_date"):
        BatchScrapeRequest(
            subreddits=["python"],
            start_date="2026-02-01",
            end_date="2026-01-01"
        )


def test_parse_iso_datetime_utc_normalization():
    """Verify that ISO datetimes are parsed and normalized to UTC."""
    # Zulu format
    dt, fallback = parse_iso_datetime("2026-05-15T12:00:00Z")
    assert not fallback
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 12

    # Offset format (+02:00)
    dt2, fallback2 = parse_iso_datetime("2026-05-15T14:00:00+02:00")
    assert not fallback2
    assert dt2.tzinfo == timezone.utc
    assert dt2.hour == 12  # 14:00+02:00 is 12:00 UTC

    # Malformed timestamp fallback
    dt_fallback, is_fallback = parse_iso_datetime("invalid-timestamp-string")
    assert is_fallback
    assert dt_fallback.tzinfo == timezone.utc


def test_make_comment_id_deterministic_bigint():
    """Verify comment ID hashing is deterministic and fits in PostgreSQL BigInteger."""
    id1 = _make_comment_id("ext_123", "author_a", "Hello world")
    id2 = _make_comment_id("ext_123", "author_a", "Hello world")
    assert id1 == id2
    assert 0 < id1 < 2**63 - 1


@pytest.mark.asyncio
async def test_run_subreddit_etl_rejects_invalid_date_inputs(monkeypatch):
    """Verify that run_subreddit_etl immediately rejects malformed date parameters."""
    monkeypatch.setattr(settings, "apify_api_token", "fake_token")

    with pytest.raises(ValueError, match="Invalid start_date format"):
        await run_subreddit_etl("python", start_date="bad-date")

    with pytest.raises(ValueError, match="Invalid end_date format"):
        await run_subreddit_etl("python", end_date="bad-date")

    with pytest.raises(ValueError, match="cannot be after end_date"):
        await run_subreddit_etl("python", start_date="2026-05-10", end_date="2026-05-01")


@pytest.mark.asyncio
async def test_idempotent_ingestion_and_comment_deduplication(monkeypatch):
    """
    Verify that repeatedly ingesting the same post and comment items
    does not create duplicate rows in the database.
    """
    monkeypatch.setattr(settings, "apify_api_token", "dummy_token")

    # In-memory SQLite with registered JSON adapter
    import sqlite3
    import json
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.dialects.postgresql import ARRAY

    @compiles(ARRAY, "sqlite")
    def compile_array_sqlite(element, compiler, **kw):
        return "JSON"

    sqlite3.register_adapter(list, json.dumps)
    sqlite3.register_converter("JSON", json.loads)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # Mock Apify actor dataset response
    sample_items = [
        {
            "id": "post_item_1",
            "parsedId": "p1",
            "dataType": "post",
            "url": "https://reddit.com/r/python/comments/p1/test_post",
            "title": "Learning Python in 2026",
            "author": "u/learner",
            "score": 42,
            "numComments": 1,
            "text": "What are best practices for FastAPI?",
            "createdAt": "2026-06-01T10:00:00Z"
        },
        {
            "id": "comment_item_1",
            "postId": "p1",
            "dataType": "comment",
            "username": "u/expert",
            "body": "Always use dependency injection and asyncpg.",
            "upvotes": 10,
            "createdAt": "2026-06-01T10:15:00Z"
        }
    ]

    class FakeDataset:
        async def list_items(self):
            class ItemsContainer:
                items = sample_items
            return ItemsContainer()

    class FakeRun:
        id = "mock_run_id"
        default_dataset_id = "mock_dataset_id"

    class FakeActor:
        async def call(self, run_input):
            return FakeRun()

    class FakeApifyClient:
        def __init__(self, token):
            pass
        def actor(self, actor_id):
            return FakeActor()
        def dataset(self, dataset_id):
            return FakeDataset()

    monkeypatch.setattr("backend.etl.pipeline.ApifyClientAsync", FakeApifyClient)

    # Run ingestion Pass 1
    res1 = await run_subreddit_etl("python", post_limit=1, comment_limit=1, session_maker=session_maker)
    assert res1["status"] == "success"
    assert res1["posts_scraped"] == 1
    assert res1["comments_scraped"] == 1

    # Verify counts in DB
    async with session_maker() as session:
        posts = (await session.execute(select(Post))).scalars().all()
        comments = (await session.execute(select(Comment))).scalars().all()
        assert len(posts) == 1
        assert len(comments) == 1

    # Run ingestion Pass 2 (Same items fetched again)
    res2 = await run_subreddit_etl("python", post_limit=1, comment_limit=1, session_maker=session_maker)
    assert res2["status"] == "success"

    # Verify no duplicate posts or comments were created
    async with session_maker() as session:
        posts_after = (await session.execute(select(Post))).scalars().all()
        comments_after = (await session.execute(select(Comment))).scalars().all()
        assert len(posts_after) == 1
        assert len(comments_after) == 1

    await engine.dispose()
