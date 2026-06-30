from __future__ import annotations

import httpx

from backend.config import settings
from backend.services.api_key_manager import api_key_manager


class EmbeddingService:
    OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

    async def _generate(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        headers = {
            "Authorization": f"Bearer {api_key_manager.get_next_key()}",
            "Content-Type": "application/json",
        }
        json_data = {
            "input": texts,
            "model": settings.openrouter_embedding_model,
        }
        url = f"{self.OPENROUTER_API_BASE}/embeddings"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=json_data)
            response.raise_for_status()
            payload = response.json()

        if not payload.get("data"):
            raise RuntimeError("Unexpected embedding response from OpenRouter")

        return [entry["embedding"] for entry in payload["data"]]

    async def generate_embedding(self, text: str) -> list[float]:
        if not text:
            return []
        embeddings = await self._generate([text])
        return embeddings[0] if embeddings else []

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        return await self._generate(texts)
