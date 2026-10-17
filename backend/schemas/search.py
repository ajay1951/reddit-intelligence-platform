from __future__ import annotations

from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=50)


class SearchResult(BaseModel):
    id: str
    document: str
    metadata: dict[str, str | int | None]
    distance: float | None


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


from typing import Literal


class RagRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=50)
    mode: Literal["keyword", "semantic", "hybrid", "hybrid_reranked"] = Field(
        "hybrid", description="Retrieval pipeline mode"
    )



class RagResponse(BaseModel):
    query: str
    answer: str
    sources: list[SearchResult]
