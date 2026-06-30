from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, field_validator
import json
import re
import redis.asyncio as redis
import os

from backend.database.connection import get_session
from backend.agents.coordinator import DeepResearchCoordinator
from backend.api.limiter import limiter
from backend.config import settings

router = APIRouter()

# Initialize Redis pool
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class DeepResearchRequest(BaseModel):
    topic: str = Field(..., max_length=150, description="The topic to research")

    @field_validator('topic')
    @classmethod
    def sanitize_topic(cls, v: str) -> str:
        # Strip excessive whitespace and purely malicious injection characters
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Topic must be at least 3 characters long")
        # Remove typical injection characters
        sanitized = re.sub(r'[;<>{}\[\]\\]', '', v)
        return sanitized

@router.post("")
@limiter.limit("5/minute")
async def run_deep_research(
    request_http: Request,
    request: DeepResearchRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Kicks off a multi-agent deep research process and streams the Chain-of-Thought
    progress back to the client using Server-Sent Events (SSE).
    Has Redis Response Caching and Rate Limiting.
    """
    coordinator = DeepResearchCoordinator()
    
    # Check cache first
    cache_key = f"deep_research:{request.topic.lower().strip()}"
    try:
        cached_report = await redis_client.get(cache_key)
        if cached_report:
            async def cached_stream():
                yield f"data: {json.dumps({'step': 'final', 'data': cached_report})}\n\n"
            return StreamingResponse(cached_stream(), media_type="text/event-stream")
    except Exception as e:
        # If redis fails, log and continue without cache
        pass

    async def event_stream():
        final_report = None
        async for step_result in coordinator.conduct_deep_research(session, request.topic):
            if step_result.get('step') == 'final':
                final_report = step_result.get('data')
            yield f"data: {json.dumps(step_result)}\n\n"
            
        # Save to cache after streaming completes
        if final_report:
            try:
                await redis_client.setex(cache_key, 86400, final_report) # 24 hr cache
            except Exception:
                pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")
