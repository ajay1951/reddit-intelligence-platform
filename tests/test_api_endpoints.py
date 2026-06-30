from __future__ import annotations

from fastapi.testclient import TestClient

from backend.config import settings
from backend.schemas.comment import CommentSchema
from backend.schemas.insight import SkillSchema, TrendResponse
from backend.schemas.post import PostSchema
from backend.schemas.subreddit import SubredditSchema
from backend.scripts.run_scraper import app


def _disable_scheduler(monkeypatch):
    monkeypatch.setattr(settings, "scheduler_enabled", False)
    monkeypatch.setattr("backend.scripts.run_scraper.start_scheduler", lambda: None)


def test_get_posts_endpoint(monkeypatch):
    async def fake_list_posts(self, session, limit, offset, subreddit):
        return [
            PostSchema(
                id=1,
                title="Test post",
                author="u/test",
                subreddit="python",
                score=10,
                comments_count=2,
                url="https://old.reddit.com/r/python/comments/1/test",
                content="Example content",
                created_at=None,
                scraped_at=None,
            )
        ]

    monkeypatch.setattr(
        "backend.services.post_service.PostService.list_posts",
        fake_list_posts,
    )
    _disable_scheduler(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/posts")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "title": "Test post",
            "author": "u/test",
            "subreddit": "python",
            "score": 10,
            "comments_count": 2,
            "url": "https://old.reddit.com/r/python/comments/1/test",
            "content": "Example content",
            "created_at": None,
            "scraped_at": None,
        }
    ]


def test_get_comments_endpoint(monkeypatch):
    async def fake_list_comments(self, session, limit, offset, post_id, subreddit):
        return [
            CommentSchema(
                id=123,
                post_id=1,
                post_url="https://old.reddit.com/r/python/comments/1/test",
                subreddit="python",
                author="u/test",
                content="Sample comment",
                score=5,
                created_at=None,
            )
        ]

    monkeypatch.setattr(
        "backend.services.comment_service.CommentService.list_comments",
        fake_list_comments,
    )
    _disable_scheduler(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/comments")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 123,
            "post_id": 1,
            "post_url": "https://old.reddit.com/r/python/comments/1/test",
            "subreddit": "python",
            "author": "u/test",
            "content": "Sample comment",
            "score": 5,
            "created_at": None,
        }
    ]


def test_get_subreddits_endpoint(monkeypatch):
    async def fake_list_subreddits(self, session, limit, offset):
        return [
            SubredditSchema(
                id=1,
                name="python",
                url="https://old.reddit.com/r/python/",
                created_at=None,
                post_count=42,
            )
        ]

    monkeypatch.setattr(
        "backend.services.subreddit_service.SubredditService.list_subreddits",
        fake_list_subreddits,
    )
    _disable_scheduler(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/subreddits")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "python",
            "url": "https://old.reddit.com/r/python/",
            "created_at": None,
            "post_count": 42,
        }
    ]


def test_get_skills_endpoint(monkeypatch):
    async def fake_get_skills(self, session, limit):
        return [SkillSchema(name="python", count=10)]

    monkeypatch.setattr(
        "backend.services.insight_service.InsightService.get_skills",
        fake_get_skills,
    )
    _disable_scheduler(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/skills")

    assert response.status_code == 200
    assert response.json() == [{"name": "python", "count": 10}]


def test_get_trends_endpoint(monkeypatch):
    async def fake_get_trends(self, session, limit):
        return TrendResponse(
            top_subreddits=[{"subreddit": "python", "count": 5}],
            top_keywords=[{"keyword": "python", "count": 10}],
        )

    monkeypatch.setattr(
        "backend.services.insight_service.InsightService.get_trends",
        fake_get_trends,
    )
    _disable_scheduler(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/trends")

    assert response.status_code == 200
    assert response.json() == {
        "top_subreddits": [{"subreddit": "python", "count": 5}],
        "top_keywords": [{"keyword": "python", "count": 10}],
    }
