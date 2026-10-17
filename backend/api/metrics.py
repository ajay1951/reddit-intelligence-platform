"""
Lightweight application metrics collector and reporter.
Tracks HTTP requests, latencies, status codes, Celery tasks, and cache metrics
without external agent dependencies.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any
from fastapi import APIRouter

router = APIRouter(tags=["observability"])


class MetricsCollector:
    _instance: MetricsCollector | None = None

    def __new__(cls) -> MetricsCollector:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_metrics()
        return cls._instance

    def _init_metrics(self) -> None:
        self.start_time = time.time()
        self.request_count = 0
        self.status_codes: dict[str, int] = defaultdict(int)
        self.endpoint_latencies: dict[str, list[float]] = defaultdict(list)
        self.cache_hits = 0
        self.cache_misses = 0
        self.task_successes = 0
        self.task_failures = 0

    def record_request(self, endpoint: str, status_code: int, duration_ms: float) -> None:
        self.request_count += 1
        self.status_codes[str(status_code)] += 1
        # Keep sliding window of latest 100 latencies per endpoint to bound memory
        latencies = self.endpoint_latencies[endpoint]
        latencies.append(round(duration_ms, 2))
        if len(latencies) > 100:
            latencies.pop(0)

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        self.cache_misses += 1

    def record_task_result(self, success: bool) -> None:
        if success:
            self.task_successes += 1
        else:
            self.task_failures += 1

    def get_summary(self) -> dict[str, Any]:
        uptime_seconds = round(time.time() - self.start_time, 2)
        
        endpoint_stats = {}
        for ep, lats in self.endpoint_latencies.items():
            if lats:
                sorted_lats = sorted(lats)
                n = len(sorted_lats)
                p50 = sorted_lats[int(n * 0.5)]
                p95 = sorted_lats[min(int(n * 0.95), n - 1)]
                endpoint_stats[ep] = {
                    "count": len(lats),
                    "avg_ms": round(sum(lats) / n, 2),
                    "p50_ms": p50,
                    "p95_ms": p95,
                }

        total_cache = self.cache_hits + self.cache_misses
        cache_hit_rate = round(self.cache_hits / total_cache, 4) if total_cache > 0 else 1.0

        return {
            "uptime_seconds": uptime_seconds,
            "requests": {
                "total": self.request_count,
                "status_codes": dict(self.status_codes),
                "endpoints": endpoint_stats,
            },
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": cache_hit_rate,
            },
            "background_tasks": {
                "successes": self.task_successes,
                "failures": self.task_failures,
            },
        }


metrics = MetricsCollector()
metrics_collector = metrics


@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """Exposes real-time application metrics and operational telemetry."""
    return metrics.get_summary()


@router.get("/metrics/llm")
async def get_llm_metrics() -> dict[str, Any]:
    """Exposes real-time LLM token consumption, latency percentiles, and inference cost."""
    from backend.services.telemetry_service import telemetry_service
    return telemetry_service.get_summary()

