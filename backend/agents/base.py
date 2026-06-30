import httpx
import structlog
from typing import Optional

from backend.config import settings
from backend.services.api_key_manager import api_key_manager

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger(__name__)

class BaseAgent:
    OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

    def __init__(self, name: str, default_model: Optional[str] = None):
        self.name = name
        self.default_model = default_model or settings.openrouter_rag_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True
    )
    async def _execute_with_retry(self, system_prompt: str, user_prompt: str, model: str) -> str:
        return await self._execute_call(system_prompt, user_prompt, model)

    async def call_llm(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        model = model or self.default_model
        models_to_try = [model]
        
        if settings.openrouter_fallback_rag_models:
            fallbacks = [m.strip() for m in settings.openrouter_fallback_rag_models.split(",") if m.strip()]
            for fallback in fallbacks:
                if fallback not in models_to_try:
                    models_to_try.append(fallback)

        last_error = None
        for current_model in models_to_try:
            try:
                return await self._execute_with_retry(system_prompt, user_prompt, current_model)
            except Exception as e:
                logger.warning(f"[{self.name}] Model {current_model} failed. Falling back. Error: {str(e)}")
                last_error = e
                continue

        raise RuntimeError(f"[{self.name}] All fallback models exhausted due to rate limits or errors. Last error: {str(last_error)}")

    async def _execute_call(self, system_prompt: str, user_prompt: str, model: str) -> str:
        headers = {
            "Authorization": f"Bearer {api_key_manager.get_next_key()}",
            "Content-Type": "application/json",
        }
        json_data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        url = f"{self.OPENROUTER_API_BASE}/chat/completions"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=json_data)
            response.raise_for_status()
            payload = response.json()

        if choices := payload.get("choices"):
            if isinstance(choices, list) and choices:
                message = choices[0].get("message")
                if isinstance(message, dict) and message.get("content"):
                    return message["content"]

        raise RuntimeError(f"[{self.name}] Unexpected completion response from OpenRouter: {payload}")
