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

# Instantiate services globally so AI models are loaded into memory once at startup,
# instead of reloading from disk on every single API request.
_semantic_service = SemanticService()
_rag_service = RagService(semantic_service=_semantic_service)


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> SemanticSearchResponse:
    results = await _semantic_service.semantic_search(request.query, top_k=request.top_k)
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
    count = await _semantic_service.index_documents(session)
    return {"indexed_documents": count}


@router.post("/rag", response_model=RagResponse)
async def rag_query(request: RagRequest, session: AsyncSession = Depends(get_session)) -> RagResponse:
    answer, sources = await _rag_service.answer_query(session, request.query, top_k=request.top_k)
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
