from __future__ import annotations

import httpx
import structlog
import asyncio
from backend.config import settings

logger = structlog.get_logger(__name__)

class EmbeddingService:
    EXPECTED_DIM = 384

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.hf_embedding_model or "BAAI/bge-small-en-v1.5"
        self.api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
        self.headers = {"Authorization": f"Bearer {settings.hf_api_key}"}
        self._client: httpx.AsyncClient | None = None
        logger.info(f"Using Hugging Face API for embeddings: {self.model_name}")

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _query(self, payload: dict, max_retries: int = 5) -> list:
        client = self._get_client()
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
        if not text or not text.strip():
            return []
        result = await self._query({"inputs": text})
        if isinstance(result, list) and result and isinstance(result[0], (int, float)):
            dim = len(result)
            if dim != self.EXPECTED_DIM:
                logger.warning(f"Embedding dimension {dim} deviates from expected {self.EXPECTED_DIM}")
            return [float(x) for x in result]
        elif isinstance(result, list) and result and isinstance(result[0], list):
            # Sometimes single inputs return nested [[...]]
            vec = [float(x) for x in result[0]]
            return vec
        return []

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        if not valid_indices:
            return [[] for _ in texts]
        
        inputs = [texts[i] for i in valid_indices]
        raw_result = await self._query({"inputs": inputs})
        
        if not isinstance(raw_result, list):
            logger.error(f"Unexpected response format from embedding API: {type(raw_result)}")
            return [[] for _ in texts]

        # Reconstruct full list with empty lists for blanks
        embeddings: list[list[float]] = [[] for _ in texts]
        for idx, valid_idx in enumerate(valid_indices):
            if idx < len(raw_result) and isinstance(raw_result[idx], list):
                vec = [float(x) for x in raw_result[idx]]
                if len(vec) != self.EXPECTED_DIM:
                    logger.warning(f"Batch embedding dimension {len(vec)} deviates from expected {self.EXPECTED_DIM}")
                embeddings[valid_idx] = vec
        return embeddings


