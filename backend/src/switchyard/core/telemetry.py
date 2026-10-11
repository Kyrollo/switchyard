from __future__ import annotations

import time
from typing import Callable
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog

# Metrics definition
HTTP_REQUESTS_TOTAL = Counter(
    "switchyard_http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "switchyard_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

LLM_CALLS_TOTAL = Counter(
    "switchyard_llm_calls_total",
    "Total LLM calls executed",
    ["model", "status"],
)

LLM_CALL_DURATION_SECONDS = Histogram(
    "switchyard_llm_call_duration_seconds",
    "Latency of LLM calls in seconds",
    ["model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Logger setup
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger("switchyard")


async def telemetry_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    start_time = time.perf_counter()
    method = request.method
    path = request.url.path

    try:
        response = await call_next(request)
        duration = time.perf_counter() - start_time
        status_code = str(response.status_code)

        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status=status_code).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=path).observe(duration)
        return response
    except Exception as exc:
        duration = time.perf_counter() - start_time
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status="500").inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=path).observe(duration)
        logger.error("request_failed", method=method, path=path, error=str(exc))
        raise
