from __future__ import annotations

from fastapi.testclient import TestClient

from backend.config import settings
from backend.schemas.search import RagResponse, SemanticSearchResponse
from backend.scripts.run_scraper import app


def _disable_scheduler(monkeypatch):
    monkeypatch.setattr(settings, "scheduler_enabled", False)
    monkeypatch.setattr("backend.scripts.run_scraper.start_scheduler", lambda: None)


def test_semantic_search_endpoint(monkeypatch):
    async def fake_semantic_search(self, query, top_k):
        return [
            {
                "id": "post-1",
                "document": "Example document",
                "metadata": {"type": "post", "subreddit": "python"},
                "distance": 0.12,
            }
        ]

    monkeypatch.setattr(
        "backend.services.semantic_service.SemanticService.semantic_search",
        fake_semantic_search,
    )
    _disable_scheduler(monkeypatch)

    with TestClient(app) as client:
        response = client.post("/search/semantic", json={"query": "python hiring", "top_k": 1})

    assert response.status_code == 200
    assert response.json() == {
        "query": "python hiring",
        "results": [
            {
                "id": "post-1",
                "document": "Example document",
                "metadata": {"type": "post", "subreddit": "python"},
                "distance": 0.12,
            }
        ],
    }


def test_reindex_vectors_endpoint(monkeypatch):
    async def fake_index_documents(self, session):
        return 42

    monkeypatch.setattr(
        "backend.services.semantic_service.SemanticService.index_documents",
        fake_index_documents,
    )
    _disable_scheduler(monkeypatch)

    with TestClient(app) as client:
        response = client.post("/search/reindex")

    assert response.status_code == 200
    assert response.json() == {"indexed_documents": 42}


def test_rag_endpoint(monkeypatch):
    async def fake_answer_query(self, query, top_k):
        return (
            "This answer uses retrieved context.",
            [
                {
                    "id": "comment-123",
                    "document": "Context snippet",
                    "metadata": {"type": "comment", "subreddit": "python"},
                    "distance": 0.05,
                }
            ],
        )

    monkeypatch.setattr(
        "backend.services.rag_service.RagService.answer_query",
        fake_answer_query,
    )
    _disable_scheduler(monkeypatch)

    with TestClient(app) as client:
        response = client.post("/search/rag", json={"query": "What hiring signals exist?", "top_k": 1})

    assert response.status_code == 200
    assert response.json() == {
        "query": "What hiring signals exist?",
        "answer": "This answer uses retrieved context.",
        "sources": [
            {
                "id": "comment-123",
                "document": "Context snippet",
                "metadata": {"type": "comment", "subreddit": "python"},
                "distance": 0.05,
            }
        ],
    }
