import asyncio

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base, Subreddit, Post


@pytest.mark.asyncio
async def test_models_create_and_query():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        sr = Subreddit(name="testsub", url="https://old.reddit.com/r/testsub/")
        session.add(sr)
        await session.flush()

        p = Post(title="Hello", author="u/test", subreddit=sr, score=10, comments_count=0, url="https://old.reddit.com/testpost")
        session.add(p)
        await session.commit()

        res = await session.get(Post, p.id)
        assert res.title == "Hello"
