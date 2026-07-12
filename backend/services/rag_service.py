from __future__ import annotations

import httpx
import structlog

from backend.config import settings
from backend.services.semantic_service import SemanticService
from backend.services.reranker_service import RerankerService
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

class RagService:
    GROQ_API_BASE = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        semantic_service: SemanticService | None = None,
        reranker_service: RerankerService | None = None,
    ) -> None:
        self.semantic_service = semantic_service or SemanticService()
        self.reranker_service = reranker_service or RerankerService()

    async def answer_query(self, session: AsyncSession, query: str, top_k: int = 5) -> tuple[str, list[dict[str, str | int | None]]]:
        # Perform hybrid search fetching more candidates
        candidate_sources = await self.semantic_service.hybrid_search(session, query, top_k=top_k * 3)
        
        # Rerank candidates
        sources = await self.reranker_service.rerank(query, candidate_sources, top_k=top_k)
        if not sources:
            return "No relevant documents found to answer your query.", []

        context_lines = []
        for source in sources:
            metadata = source.get("metadata", {}) or {}
            header = f"Source: {metadata.get('type', 'unknown')}"
            if metadata.get("subreddit"):
                header += f" | subreddit: {metadata['subreddit']}"
            context_lines.append(header)
            context_lines.append(source["document"])
            context_lines.append("---")

        system_prompt = (
            "You are a helpful AI research assistant that analyzes Reddit hiring intelligence. "
            "Use only the context below to assist the user. "
            "If the user asks a question, answer it directly using the context. "
            "If the user provides just a topic or keyword (like 'python' or 'remote'), summarize what the context says about that topic. "
            "If the context contains absolutely no relevant information, say that you do not have enough data."
        )
        user_prompt = "Context:\n" + "\n".join(context_lines) + "\n\nQuestion: " + query

        model = settings.groq_model

        try:
            answer = await self._call_groq(system_prompt, user_prompt, model)
            return answer, sources
        except Exception as e:
            logger.error(f"Model {model} failed. Error: {str(e)}")
            return "I apologize, but I am currently unable to process your request due to system rate limits or connectivity issues. Please try again later.", []

    async def _call_groq(self, system_prompt: str, user_prompt: str, model: str) -> str:
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        json_data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        url = f"{self.GROQ_API_BASE}/chat/completions"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=json_data)
            response.raise_for_status()
            payload = response.json()

        if choices := payload.get("choices"):
            if isinstance(choices, list) and choices:
                message = choices[0].get("message")
                if isinstance(message, dict) and message.get("content"):
                    return message["content"]

        raise RuntimeError(f"Unexpected completion response from Groq: {payload}")
