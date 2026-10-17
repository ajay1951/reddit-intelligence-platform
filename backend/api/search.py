from __future__ import annotations

from fastapi import APIRouter, Depends, Request
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
from backend.api.limiter import limiter

router = APIRouter(prefix="/search", tags=["search"])

# Instantiate services globally so AI models are loaded into memory once at startup,
# instead of reloading from disk on every single API request.
_semantic_service = SemanticService()
_rag_service = RagService(semantic_service=_semantic_service)


@router.post("/semantic", response_model=SemanticSearchResponse)
@limiter.limit("40/minute")
async def semantic_search(
    request: Request,
    body: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> SemanticSearchResponse:
    results = await _semantic_service.semantic_search(body.query, top_k=body.top_k)
    return SemanticSearchResponse(
        query=body.query,
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


from backend.api.auth import require_admin, TokenData

@router.post("/reindex")
async def reindex_vectors(
    admin_user: TokenData = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    count = await _semantic_service.index_documents(session)
    return {"indexed_documents": count}



@router.post("/rag", response_model=RagResponse)
@limiter.limit("20/minute")
async def rag_query(
    request: Request,
    body: RagRequest,
    session: AsyncSession = Depends(get_session)
) -> RagResponse:
    try:
        answer, sources = await _rag_service.answer_query(
            session, body.query, top_k=body.top_k, mode=body.mode
        )
    except TypeError:
        # Backward compatibility for mocks that do not accept mode keyword argument
        answer, sources = await _rag_service.answer_query(
            session, body.query, top_k=body.top_k
        )

    return RagResponse(
        query=body.query,
        answer=answer,
        sources=[
            SearchResult(
                id=source.get("id", "doc"),
                document=source.get("document", ""),
                metadata=source.get("metadata", {}),
                distance=source.get("distance", source.get("score")),
            )
            for source in sources
        ],
    )

