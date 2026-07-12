from __future__ import annotations

import httpx
import structlog
import asyncio
from backend.config import settings

logger = structlog.get_logger(__name__)

class RerankerService:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        self.headers = {"Authorization": f"Bearer {settings.hf_api_key}"}
        logger.info(f"Using Hugging Face API for reranker: {self.model_name}")

    async def _query(self, payload: dict, max_retries: int = 5) -> list:
        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(self.api_url, headers=self.headers, json=payload, timeout=30.0)
                    response.raise_for_status()
                    result = response.json()
                    
                    if isinstance(result, dict) and "error" in result:
                        if "is currently loading" in result.get("error", ""):
                            wait_time = result.get("estimated_time", 20.0)
                            logger.info(f"Reranker is loading, waiting {wait_time}s", attempt=attempt)
                            await asyncio.sleep(wait_time)
                            continue
                        raise Exception(f"HF API Error: {result['error']}")
                    return result
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 503:
                        logger.info("503 Reranker is loading, waiting 10s", attempt=attempt)
                        await asyncio.sleep(10)
                        continue
                    raise e
                except Exception as e:
                    logger.error(f"Error querying HF Reranker API: {e}")
                    raise e
        raise Exception("Max retries exceeded waiting for reranker to load.")

    async def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        if not documents:
            return []

        pairs = [[query, doc["document"]] for doc in documents]
        payload = {"inputs": pairs}
        
        try:
            scores = await self._query(payload)
            if scores and isinstance(scores[0], dict) and "score" in scores[0]:
                for i, doc in enumerate(documents):
                    doc["rerank_score"] = float(scores[i]["score"])
            else:
                for i, doc in enumerate(documents):
                    doc["rerank_score"] = float(scores[i])
                    
            ranked_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
            return ranked_docs[:top_k]
        except Exception as e:
            logger.error("Reranking failed via API", error=str(e))
            return documents[:top_k]
