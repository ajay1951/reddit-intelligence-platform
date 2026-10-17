import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from backend.services.embedding_service import EmbeddingService
from backend.services.reranker_service import RerankerService
from backend.repositories.chroma_repository import ChromaRepository
from backend.services.semantic_service import SemanticService


@pytest.mark.asyncio
async def test_embedding_service_dimensions_and_validation():
    service = EmbeddingService()
    
    # 1. Empty string test
    assert await service.generate_embedding("") == []
    assert await service.generate_embedding("   ") == []
    assert await service.generate_embeddings([]) == []

    # 2. Mock 384-dim vector response
    mock_vec = [0.05] * 384
    with patch.object(service, "_query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_vec
        res = await service.generate_embedding("FastAPI database session")
        assert len(res) == 384
        assert res[0] == 0.05

    # 3. Batch embeddings
    with patch.object(service, "_query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = [mock_vec, mock_vec]
        batch_res = await service.generate_embeddings(["query 1", "query 2"])
        assert len(batch_res) == 2
        assert len(batch_res[0]) == 384
        assert len(batch_res[1]) == 384

    await service.aclose()


def test_chroma_upsert_idempotency():
    repo = ChromaRepository()
    test_id = "test-post-phase2"
    doc1 = "Initial post content"
    doc2 = "Updated post content idempotency check"
    meta = {"type": "post", "url": "https://reddit.com/test"}

    # First insertion
    repo.add_documents(ids=[test_id], documents=[doc1], metadatas=[meta])
    
    # Second insertion with same ID should not raise IDAlreadyExists
    repo.upsert_documents(ids=[test_id], documents=[doc2], metadatas=[meta])
    
    # Query to verify it succeeded
    query_res = repo.query(n_results=1, query_text="idempotency check")
    assert query_res is not None
    # Clean up
    repo.delete_documents([test_id])


def test_hybrid_retrieval_rrf_scoring():
    service = SemanticService()
    
    dense_results = [
        {"id": "doc-1", "document": "Dense result 1", "metadata": {}},
        {"id": "doc-2", "document": "Dense result 2", "metadata": {}},
    ]
    sparse_results = [
        {"id": "doc-2", "document": "Sparse result 2", "metadata": {}},
        {"id": "doc-3", "document": "Sparse result 3", "metadata": {}},
    ]

    merged = service.rrf_merge(dense_results, sparse_results, k=60, top_k=3)
    
    assert len(merged) == 3
    # doc-2 appeared in both dense and sparse, so its RRF score must be strictly higher than doc-1 or doc-3
    assert merged[0]["id"] == "doc-2"
    assert "rrf_score" in merged[0]
    assert merged[0]["rrf_score"] > merged[1]["rrf_score"]


@pytest.mark.asyncio
async def test_reranker_fallback_behavior():
    reranker = RerankerService()
    docs = [
        {"id": "doc-1", "document": "Python backend microservices", "metadata": {}},
        {"id": "doc-2", "document": "Unrelated gardening tips", "metadata": {}},
    ]

    # Force HF API error to simulate timeout or endpoint block
    with patch.object(reranker, "_query", side_effect=Exception("API Throttled 503")):
        ranked, was_reranked = await reranker.rerank_detailed("Python microservices", docs, top_k=2)
        
        # Telemetry must confirm that reranker failed gracefully
        assert was_reranked is False
        assert len(ranked) == 2
        # Fallback lexical ranker should still score the Python document higher than gardening
        assert ranked[0]["id"] == "doc-1"
        assert ranked[0]["was_reranked"] is False

    await reranker.aclose()
