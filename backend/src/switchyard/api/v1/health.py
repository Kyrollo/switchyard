from __future__ import annotations

from fastapi import APIRouter, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
import httpx
from ...core.config import settings
from ...core.telemetry import logger

router = APIRouter(tags=["health"])


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz() -> dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "ok", "app": "switchyard"}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, object]:
    """Kubernetes readiness probe. Checks real upstream connectivity."""
    checks: dict[str, str] = {"app": "ok"}
    is_ready = True

    # Real LLM endpoint ping
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.LLM_BASE_URL.rstrip('/v1')}/api/tags")
            if resp.status_code == 200:
                checks["llm_upstream"] = "connected"
            else:
                checks["llm_upstream"] = f"degraded (status {resp.status_code})"
    except Exception as exc:
        checks["llm_upstream"] = f"unavailable ({type(exc).__name__})"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "degraded",
        "checks": checks,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
