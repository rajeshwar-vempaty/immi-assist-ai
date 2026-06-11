"""Prometheus metrics for FastAPI."""

import re
import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Normalize paths to limit metric cardinality
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM API calls",
    ["provider", "intent", "status"],
)

LLM_LATENCY = Histogram(
    "llm_request_duration_seconds",
    "LLM call latency in seconds",
    ["provider"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)


def normalize_path(path: str) -> str:
    """Collapse dynamic segments for stable Prometheus labels."""
    path = _UUID_RE.sub("{id}", path)
    parts = path.strip("/").split("/")
    if len(parts) > 4:
        return "/" + "/".join(parts[:4]) + "/..."
    return path or "/"


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        path = normalize_path(request.url.path)
        method = request.method
        status = str(response.status_code)

        HTTP_REQUESTS.labels(method=method, path=path, status=status).inc()
        HTTP_LATENCY.labels(method=method, path=path).observe(duration)

        return response


def metrics_endpoint() -> Response:
    """Expose Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def record_llm_call(provider: str, intent: str, status: str, duration: float) -> None:
    """Record an LLM provider call."""
    LLM_REQUESTS.labels(provider=provider, intent=intent, status=status).inc()
    LLM_LATENCY.labels(provider=provider).observe(duration)
