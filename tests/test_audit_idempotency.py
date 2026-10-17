from __future__ import annotations

import json
import sqlite3
import pytest
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.future import select

from backend.etl.pipeline import _make_comment_id, run_subreddit_etl
from backend.models.models import Base, Comment, Post, Subreddit


@compiles(ARRAY, "sqlite")
def compile_array_sqlite(element, compiler, **kw):
    return "JSON"


def test_comment_id_hashing_determinism_and_bounds():
    """Verify comment ID hashing is deterministic, cross-process stable, and within positive 63-bit bounds."""
    # Test identical inputs produce identical outputs
    id_a = _make_comment_id("ext_abc", "author_1", "Some test content")
    id_b = _make_comment_id("ext_abc", "author_1", "Some test content")
    assert id_a == id_b

    # Verify bounds (PostgreSQL BIGINT positive range is 1 to 2^63 - 1)
    assert 1 <= id_a < 2**63 - 1

    # Verify missing optional fields do not throw or produce invalid integers
    id_none = _make_comment_id(None, None, "Content only")
    assert isinstance(id_none, int)
    assert 1 <= id_none < 2**63 - 1

    # Verify different external IDs produce distinct comment IDs
    id_diff = _make_comment_id("ext_xyz", "author_1", "Some test content")
    assert id_a != id_diff

    # Verify different content produces distinct comment IDs even with identical author
    id_content_diff = _make_comment_id("ext_abc", "author_1", "Different content")
    assert id_a != id_content_diff


@pytest.mark.asyncio
async def test_idempotent_ingestion_double_run(monkeypatch):
    """Verify that ingesting the exact same subreddit batch twice results in zero duplicate records."""
    sqlite3.register_adapter(list, json.dumps)
    sqlite3.register_converter("JSON", json.loads)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    sample_items = [
        {
            "id": "post_item_100",
            "parsedId": "post_p1",
            "dataType": "post",
            "url": "https://reddit.com/r/python/comments/post_p1/idempotency_post",
            "title": "Idempotency Architecture in Python",
            "author": "u/idempotent_coder",
            "score": 100,
            "numComments": 2,
            "text": "How do you guarantee deduplication across pipeline retries?",
            "createdAt": "2026-07-01T10:00:00Z",
        },
        {
            "id": "comment_item_201",
            "postId": "post_p1",
            "dataType": "comment",
            "username": "u/sre_engineer",
            "body": "Use deterministic hashing and UPSERT semantics.",
            "upvotes": 25,
            "createdAt": "2026-07-01T10:05:00Z",
        },
        {
            "id": "comment_item_202",
            "postId": "post_p1",
            "dataType": "comment",
            "username": "u/db_admin",
            "body": "Always verify unique constraints on business identifiers.",
            "upvotes": 15,
            "createdAt": "2026-07-01T10:10:00Z",
        },
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

    # Ingestion Pass 1
    res1 = await run_subreddit_etl("python", post_limit=1, comment_limit=2, session_maker=session_maker)
    assert res1["status"] == "success"
    assert res1["posts_scraped"] == 1
    assert res1["comments_scraped"] == 2

    # Query database counts after Pass 1
    async with session_maker() as session:
        posts_p1 = (await session.execute(select(Post))).scalars().all()
        comments_p1 = (await session.execute(select(Comment))).scalars().all()
        assert len(posts_p1) == 1
        assert len(comments_p1) == 2

    # Ingestion Pass 2 (identical duplicate payload)
    res2 = await run_subreddit_etl("python", post_limit=1, comment_limit=2, session_maker=session_maker)
    assert res2["status"] == "success"

    # Query database counts after Pass 2 -> must be strictly identical!
    async with session_maker() as session:
        posts_p2 = (await session.execute(select(Post))).scalars().all()
        comments_p2 = (await session.execute(select(Comment))).scalars().all()
        assert len(posts_p2) == 1, "Duplicate post was inserted!"
        assert len(comments_p2) == 2, "Duplicate comments were inserted!"
        assert posts_p2[0].url == posts_p1[0].url
