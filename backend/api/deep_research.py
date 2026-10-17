from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, field_validator
import asyncio
import hashlib
import json
import re
import redis.asyncio as redis
import os
import structlog

from backend.database.connection import get_session
from backend.agents.coordinator import DeepResearchCoordinator
from backend.api.limiter import limiter
from backend.config import settings
from backend.api.auth import get_current_user, TokenData

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize Redis pool
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class DeepResearchRequest(BaseModel):
    topic: str = Field(..., max_length=150, description="The topic to research")

    @field_validator('topic')
    @classmethod
    def sanitize_topic(cls, v: str) -> str:
        # Strip excessive whitespace and validate minimum meaningful topic length
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Topic must be at least 3 characters long")
        # Remove typical injection characters
        sanitized = re.sub(r'[;<>{}\[\]\\]', '', v)
        return sanitized


@router.post("")
@limiter.limit("5/minute")
async def run_deep_research(
    request: Request,
    body: DeepResearchRequest,
    session: AsyncSession = Depends(get_session),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Kicks off a multi-agent deep research process and streams the Chain-of-Thought
    progress back to the client using Server-Sent Events (SSE).
    Uses versioned Redis Response Caching, Rate Limiting, and Client Disconnection Auditing.
    """
    coordinator = DeepResearchCoordinator()
    
    # Versioned cache key using SHA-256 topic fingerprint
    topic_hash = hashlib.sha256(body.topic.lower().strip().encode("utf-8")).hexdigest()[:16]
    cache_key = f"deep_research:v2:{topic_hash}"

    try:
        cached_report = await redis_client.get(cache_key)
        if cached_report:
            async def cached_stream():
                yield f"data: {json.dumps({'step': 'cached', 'status': 'complete', 'message': 'Loaded from intelligence cache.'})}\n\n"
                yield f"data: {json.dumps({'step': 'final', 'status': 'complete', 'data': cached_report})}\n\n"
            return StreamingResponse(cached_stream(), media_type="text/event-stream")
    except Exception as e:
        logger.warning("Redis cache lookup failed; proceeding with live generation", error=str(e))

    async def event_stream():
        final_report = None
        try:
            async for step_result in coordinator.conduct_deep_research(session, body.topic):
                # Audit client connection status to abort orphaned background LLM chains
                if await request.is_disconnected():
                    logger.info("Client disconnected from deep research stream", topic=body.topic)
                    break
                
                if step_result.get('step') == 'final':
                    final_report = step_result.get('data')
                
                yield f"data: {json.dumps(step_result)}\n\n"

            # Persist successful run to cache (24 hr TTL)
            if final_report and not await request.is_disconnected():
                try:
                    await redis_client.setex(cache_key, 86400, final_report)
                except Exception as e:
                    logger.warning("Failed to persist report to Redis cache", error=str(e))

        except asyncio.CancelledError:
            logger.info("Deep research SSE stream cancelled by client or runtime", topic=request.topic)
            raise
        except Exception as e:
            logger.exception("Error during deep research streaming execution", error=str(e))
            yield f"data: {json.dumps({'step': 'error', 'status': 'failed', 'message': f'Research execution encountered an error: {str(e)}'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

