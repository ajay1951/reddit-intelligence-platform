from __future__ import annotations

import httpx
import structlog
import asyncio
from backend.config import settings

logger = structlog.get_logger(__name__)

class EmbeddingService:
    def __init__(self):
        self.model_name = settings.hf_embedding_model or "BAAI/bge-small-en-v1.5"
        self.api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
        self.headers = {"Authorization": f"Bearer {settings.hf_api_key}"}
        logger.info(f"Using Hugging Face API for embeddings: {self.model_name}")

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
                            logger.info(f"Model is loading, waiting {wait_time}s", attempt=attempt)
                            await asyncio.sleep(wait_time)
                            continue
                        raise Exception(f"HF API Error: {result['error']}")
                    return result
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 503:
                        logger.info("503 Model is loading, waiting 10s", attempt=attempt)
                        await asyncio.sleep(10)
                        continue
                    raise e
                except Exception as e:
                    logger.error(f"Error querying HF API: {e}")
                    raise e
        raise Exception("Max retries exceeded waiting for model to load.")

    async def generate_embedding(self, text: str) -> list[float]:
        if not text:
            return []
        result = await self._query({"inputs": text})
        return result

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        result = await self._query({"inputs": texts})
        return result

