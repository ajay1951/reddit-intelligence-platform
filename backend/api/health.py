"""
Health and readiness probe endpoints.
Provides /health for quick liveness checks and /health/ready for deep dependency probing.
"""

from __future__ import annotations

import os
from typing import Any
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import structlog

from backend.config import settings
from backend.database.connection import get_session
from backend.repositories.chroma_repository import ChromaRepository
from backend.scheduler import get_scheduler

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, Any]:
    """Basic liveness probe confirming the HTTP process is responsive."""
    scheduler = get_scheduler() if settings.scheduler_enabled else None
    return {
        "status": "ok",
        "service": "reddit-intelligence-platform",
        "scheduler_enabled": settings.scheduler_enabled,
        "scheduler_running": scheduler.running if scheduler else False,
    }


@router.get("/health/ready")
async def readiness(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Deep readiness probe verifying critical runtime dependencies:
    - PostgreSQL database connectivity
    - Redis cache and broker responsiveness
    - ChromaDB vector store initialization
    Returns HTTP 200 if ready, or HTTP 503 if any core dependency fails.
    """
    components: dict[str, dict[str, Any]] = {}
    is_healthy = True

    # 1. Probe PostgreSQL
    try:
        res = await session.execute(text("SELECT 1"))
        val = res.scalar()
        if val == 1:
            components["database"] = {"status": "healthy", "type": "postgresql"}
        else:
            components["database"] = {"status": "unhealthy", "error": f"Unexpected response {val}"}
            is_healthy = False
    except Exception as e:
        logger.error("Database readiness check failed", error=str(e))
        components["database"] = {"status": "unhealthy", "error": str(e)}
        is_healthy = False

    # 2. Probe Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        r = redis.from_url(redis_url, decode_responses=True)
        ping_result = await r.ping()
        await r.aclose()
        if ping_result:
            components["redis"] = {"status": "healthy"}
        else:
            components["redis"] = {"status": "unhealthy", "error": "Ping failed"}
            is_healthy = False
    except Exception as e:
        logger.error("Redis readiness check failed", error=str(e))
        components["redis"] = {"status": "unhealthy", "error": str(e)}
        is_healthy = False

    # 3. Probe ChromaDB
    try:
        repo = ChromaRepository()
        doc_count = repo.collection.count()
        components["chromadb"] = {
            "status": "healthy",
            "collection": settings.chroma_collection_name,
            "indexed_count": doc_count,
        }
    except Exception as e:
        logger.error("ChromaDB readiness check failed", error=str(e))
        components["chromadb"] = {"status": "unhealthy", "error": str(e)}
        is_healthy = False

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_healthy else "degraded",
        "ready": is_healthy,
        "components": components,
    }
