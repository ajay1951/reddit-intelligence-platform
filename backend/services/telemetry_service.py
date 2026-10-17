"""
LLM Observability and Telemetry Service for Reddit Intelligence Platform.
Tracks token consumption, latency percentiles (p50, p95), call volume,
and estimated inference cost across all AI agents and RAG services.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)

# Model pricing in USD per 1,000,000 tokens (Input / Output blended approximation)
MODEL_PRICING_PER_1M: dict[str, float] = {
    "openai/gpt-oss-120b": 0.59,
    "openai/gpt-oss-20b": 0.15,
    "qwen/qwen3.8-27b": 0.20,
    "llama-3.3-70b-versatile": 0.59,
    "llama-3.1-8b-instant": 0.08,
    "default": 0.20,
}


@dataclass
class LLMCallRecord:
    timestamp: str
    caller: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    estimated_cost_usd: float
    status: str = "success"
    error_message: Optional[str] = None


class TelemetryService:
    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self._records: deque[LLMCallRecord] = deque(maxlen=max_records)
        self._total_calls: int = 0
        self._total_prompt_tokens: int = 0
        self._total_completion_tokens: int = 0
        self._total_cost_usd: float = 0.0

    def record_call(
        self,
        caller: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> LLMCallRecord:
        total_tokens = prompt_tokens + completion_tokens
        rate = MODEL_PRICING_PER_1M.get(model, MODEL_PRICING_PER_1M["default"])
        cost = (total_tokens / 1_000_000.0) * rate

        record = LLMCallRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            caller=caller,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            estimated_cost_usd=round(cost, 6),
            status=status,
            error_message=error_message,
        )

        self._records.append(record)
        self._total_calls += 1
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        self._total_cost_usd += cost

        logger.info(
            "LLM call recorded",
            caller=caller,
            model=model,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            cost_usd=round(cost, 6),
        )
        return record

    def get_summary(self) -> dict[str, Any]:
        """Calculates aggregate statistics and latency percentiles."""
        if not self._records:
            return {
                "total_calls": self._total_calls,
                "total_prompt_tokens": self._total_prompt_tokens,
                "total_completion_tokens": self._total_completion_tokens,
                "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
                "total_estimated_cost_usd": round(self._total_cost_usd, 6),
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "model_distribution": {},
                "caller_distribution": {},
                "recent_calls_sample": [],
            }

        latencies = sorted([r.latency_ms for r in self._records])
        n = len(latencies)

        def percentile(p: float) -> float:
            k = (n - 1) * p
            f = int(k)
            c = min(f + 1, n - 1)
            d0 = latencies[f] * (c - k)
            d1 = latencies[c] * (k - f)
            return round(d0 + d1, 2)

        model_counts: dict[str, int] = {}
        caller_counts: dict[str, int] = {}
        for r in self._records:
            model_counts[r.model] = model_counts.get(r.model, 0) + 1
            caller_counts[r.caller] = caller_counts.get(r.caller, 0) + 1

        recent = [asdict(r) for r in list(self._records)[-10:]]
        recent.reverse()

        return {
            "total_calls": self._total_calls,
            "total_prompt_tokens": self._total_prompt_tokens,
            "total_completion_tokens": self._total_completion_tokens,
            "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
            "total_estimated_cost_usd": round(self._total_cost_usd, 6),
            "avg_latency_ms": round(sum(latencies) / n, 2),
            "p50_latency_ms": percentile(0.50),
            "p95_latency_ms": percentile(0.95),
            "p99_latency_ms": percentile(0.99),
            "model_distribution": model_counts,
            "caller_distribution": caller_counts,
            "recent_calls_sample": recent,
        }


# Global singleton instance
telemetry_service = TelemetryService()
