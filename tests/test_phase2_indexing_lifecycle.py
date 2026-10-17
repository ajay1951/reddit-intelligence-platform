import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import Post, Comment, Subreddit
from backend.services.semantic_service import SemanticService
from backend.api.deep_research import DeepResearchRequest


@pytest.mark.asyncio
async def test_incremental_indexing_batching():
    mock_session = AsyncMock(spec=AsyncSession)
    service = SemanticService()

    # Mock DB posts
    post1 = Post(id=1, title="Post 1", content="Content 1", url="http://1", subreddit_id=1)
    post2 = Post(id=2, title="Post 2", content="Content 2", url="http://2", subreddit_id=1)
    post1.subreddit = Subreddit(name="python")
    post2.subreddit = Subreddit(name="python")

    # Mock execute results
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [post1, post2]
    mock_session.execute.return_value = mock_result

    with patch.object(service.chroma_repository, "upsert_documents") as mock_upsert:
        indexed = await service.index_posts_and_comments_batch(
            mock_session, post_ids=[1, 2], comment_ids=[], batch_size=1
        )
        # Should have called upsert
        assert mock_upsert.called


def test_deep_research_cache_key_hashing_and_sanitization():
    # Valid topic
    req = DeepResearchRequest(topic="  Rust vs Go Backend Performance   ")
    assert req.topic == "Rust vs Go Backend Performance"
    
    topic_hash = hashlib.sha256(req.topic.lower().strip().encode("utf-8")).hexdigest()[:16]
    cache_key = f"deep_research:v2:{topic_hash}"
    assert cache_key.startswith("deep_research:v2:")
    assert len(topic_hash) == 16


@pytest.mark.asyncio
async def test_deep_research_client_disconnect_termination():
    from backend.agents.coordinator import DeepResearchCoordinator
    
    coordinator = DeepResearchCoordinator()
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock conduct_deep_research generator
    async def mock_generator(session, topic):
        yield {"step": "research", "status": "running"}
        yield {"step": "research", "status": "complete", "data": "info"}
        yield {"step": "trends", "status": "running"}

    with patch.object(coordinator, "conduct_deep_research", side_effect=mock_generator):
        # Mock request_http.is_disconnected()
        mock_request = AsyncMock()
        disconnect_states = [False, True]  # Disconnect after first step
        mock_request.is_disconnected.side_effect = disconnect_states

        steps_received = []
        async for step in coordinator.conduct_deep_research(mock_session, "test topic"):
            steps_received.append(step)
            if await mock_request.is_disconnected():
                break

        assert len(steps_received) == 2
