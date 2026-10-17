from __future__ import annotations

import httpx
import structlog
import asyncio
import re
from backend.config import settings

logger = structlog.get_logger(__name__)

class RerankerService:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        self.headers = {"Authorization": f"Bearer {settings.hf_api_key}"}
        self._client: httpx.AsyncClient | None = None
        logger.info(f"Using Hugging Face API for reranker: {self.model_name}")

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _query(self, payload: dict, max_retries: int = 3) -> list:
        client = self._get_client()
        for attempt in range(max_retries):
            try:
                response = await client.post(self.api_url, headers=self.headers, json=payload, timeout=20.0)
                response.raise_for_status()
                result = response.json()
                
                if isinstance(result, dict) and "error" in result:
                    if "is currently loading" in result.get("error", ""):
                        wait_time = min(result.get("estimated_time", 10.0), 10.0)
                        logger.info(f"Reranker is loading, waiting {wait_time}s", attempt=attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    raise Exception(f"HF API Error: {result['error']}")
                return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 503 and attempt < max_retries - 1:
                    logger.info("503 Reranker is loading, waiting 5s", attempt=attempt)
                    await asyncio.sleep(5)
                    continue
                raise e
            except Exception as e:
                logger.error(f"Error querying HF Reranker API: {e}")
                raise e
        raise Exception("Max retries exceeded waiting for reranker to load.")

    def _compute_fallback_lexical_score(self, query: str, document_text: str) -> float:
        """Lightweight token overlap fallback score when neural reranker is unavailable."""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        if not q_tokens:
            return 0.0
        doc_tokens = set(re.findall(r"\w+", document_text.lower()))
        overlap = len(q_tokens & doc_tokens)
        return float(overlap) / float(len(q_tokens))

    async def rerank_detailed(
        self, query: str, documents: list[dict], top_k: int = 5
    ) -> tuple[list[dict], bool]:
        """
        Reranks documents and returns (ranked_documents, was_reranked).
        If the external reranker fails or is disabled, falls back to RRF/lexical scoring and flags was_reranked=False.
        """
        if not documents:
            return [], False

        pairs = [[query, doc.get("document", "")] for doc in documents]
        payload = {"inputs": pairs}
        
        try:
            scores = await self._query(payload)
            was_reranked = True
            
            for i, doc in enumerate(documents):
                doc_copy = doc.copy()
                if scores and isinstance(scores[0], dict) and "score" in scores[0]:
                    score_val = float(scores[i]["score"])
                elif scores and isinstance(scores, list):
                    score_val = float(scores[i])
                else:
                    score_val = 0.0
                doc_copy["rerank_score"] = score_val
                doc_copy["was_reranked"] = True
                documents[i] = doc_copy
                    
            ranked_docs = sorted(documents, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            return ranked_docs[:top_k], was_reranked
        except Exception as e:
            logger.warning("Reranking failed via API; using fallback ordering", error=str(e))
            fallback_docs = []
            for doc in documents:
                doc_copy = doc.copy()
                doc_copy["was_reranked"] = False
                # If RRF score exists, keep it; else compute lexical overlap
                if "rrf_score" in doc_copy:
                    doc_copy["rerank_score"] = doc_copy["rrf_score"]
                else:
                    doc_copy["rerank_score"] = self._compute_fallback_lexical_score(
                        query, doc_copy.get("document", "")
                    )
                fallback_docs.append(doc_copy)
            ranked_docs = sorted(fallback_docs, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            return ranked_docs[:top_k], False

    async def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        ranked_docs, _ = await self.rerank_detailed(query, documents, top_k=top_k)
        return ranked_docs

