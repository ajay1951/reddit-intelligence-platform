import asyncio
import time
import httpx
import structlog
from typing import Optional

from backend.config import settings

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = structlog.get_logger(__name__)

class BaseAgent:
    GROQ_API_BASE = "https://api.groq.com/openai/v1"

    def __init__(self, name: str, default_model: Optional[str] = None):
        self.name = name
        self.default_model = default_model or settings.groq_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True
    )
    async def _execute_with_retry(self, system_prompt: str, user_prompt: str, model: str) -> str:
        return await self._execute_call(system_prompt, user_prompt, model)

    async def call_llm(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        # Cascade fallback candidates: primary -> lightweight 20b -> versatile qwen
        primary = model or self.default_model
        candidate_models = [primary, "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
        seen = set()
        models_to_try = [m for m in candidate_models if m and not (m in seen or seen.add(m))]

        last_error = None
        for candidate in models_to_try:
            try:
                return await self._execute_call(system_prompt, user_prompt, candidate)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code == 429:
                    logger.warning(
                        f"[{self.name}] Model {candidate} hit rate limit (429). Falling back to next available model...",
                        fallback_model=candidate
                    )
                    await asyncio.sleep(1.0)
                    continue
                logger.warning(f"[{self.name}] HTTP {exc.response.status_code} on model {candidate}: {str(exc)}")
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"[{self.name}] Model {candidate} failed with {type(e).__name__}: {str(e)}")
                continue

        raise RuntimeError(f"[{self.name}] All LLM candidate models failed. Last error: {str(last_error)}")

    async def _execute_call(self, system_prompt: str, user_prompt: str, model: str) -> str:
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

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=json_data)
                response.raise_for_status()
                payload = response.json()

            latency_ms = (time.perf_counter() - start_time) * 1000.0
            usage = payload.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens", len(user_prompt) // 4)
            completion_tokens = usage.get("completion_tokens", 50)

            from backend.services.telemetry_service import telemetry_service
            telemetry_service.record_call(
                caller=self.name,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                status="success"
            )

            if choices := payload.get("choices"):
                if isinstance(choices, list) and choices:
                    message = choices[0].get("message")
                    if isinstance(message, dict) and message.get("content"):
                        return message["content"]

            raise RuntimeError(f"[{self.name}] Unexpected completion response from Groq: {payload}")
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            try:
                from backend.services.telemetry_service import telemetry_service
                telemetry_service.record_call(
                    caller=self.name,
                    model=model,
                    prompt_tokens=len(user_prompt) // 4,
                    completion_tokens=0,
                    latency_ms=latency_ms,
                    status="failed",
                    error_message=str(exc)
                )
            except Exception:
                pass
            raise exc
