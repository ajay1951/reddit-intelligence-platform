from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.search import (
    RagRequest,
    RagResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SearchResult,
)
from backend.services.rag_service import RagService
from backend.services.semantic_service import SemanticService
from backend.database.connection import get_session

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> SemanticSearchResponse:
    service = SemanticService()
    results = await service.semantic_search(request.query, top_k=request.top_k)
    return SemanticSearchResponse(
        query=request.query,
        results=[
            SearchResult(
                id=result["id"],
                document=result["document"],
                metadata=result["metadata"],
                distance=result["distance"],
            )
            for result in results
        ],
    )


@router.post("/reindex")
async def reindex_vectors(
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    service = SemanticService()
    count = await service.index_documents(session)
    return {"indexed_documents": count}


@router.post("/rag", response_model=RagResponse)
async def rag_query(request: RagRequest, session: AsyncSession = Depends(get_session)) -> RagResponse:
    service = RagService()
    answer, sources = await service.answer_query(session, request.query, top_k=request.top_k)
    return RagResponse(
        query=request.query,
        answer=answer,
        sources=[
            SearchResult(
                id=source["id"],
                document=source["document"],
                metadata=source["metadata"],
                distance=source["distance"],
            )
            for source in sources
        ],
    )
