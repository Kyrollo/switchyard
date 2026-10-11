from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    """RFC 7807 Problem Details representation."""
    type: str = Field(..., description="URI reference identifying problem type")
    title: str = Field(..., description="Short, human-readable summary of problem")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation of specific occurrence")
    instance: Optional[str] = Field(None, description="URI identifying this specific occurrence")
    code: Optional[str] = Field(None, description="Application error code")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO timestamp",
    )
    invalid_params: Optional[list[Dict[str, Any]]] = None


class AppException(Exception):
    """Base application exception that yields RFC 7807 response."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    title: str = "Internal Server Error"
    type_uri: str = "about:blank"
    code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str, *, instance: str | None = None, **kwargs: Any) -> None:
        super().__init__(detail)
        self.detail = detail
        self.instance = instance
        self.extra = kwargs


class UpstreamUnavailableException(AppException):
    """HTTP 503: Raised when upstream models or dependencies are unavailable. NEVER fake responses."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    title = "Upstream Service Unavailable"
    type_uri = "https://errors.antigravity.io/upstream-unavailable"
    code = "UPSTREAM_UNAVAILABLE"


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    title = "Resource Not Found"
    type_uri = "https://errors.antigravity.io/not-found"
    code = "NOT_FOUND"


class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    title = "Unauthorized"
    type_uri = "https://errors.antigravity.io/unauthorized"
    code = "UNAUTHORIZED"


class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    title = "Forbidden"
    type_uri = "https://errors.antigravity.io/forbidden"
    code = "FORBIDDEN"


class ValidationException(AppException):
    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
    title = "Unprocessable Content"
    type_uri = "https://errors.antigravity.io/validation-error"
    code = "VALIDATION_ERROR"


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    problem = ProblemDetails(
        type=exc.type_uri,
        title=exc.title,
        status=exc.status_code,
        detail=exc.detail,
        instance=exc.instance or str(request.url),
        code=exc.code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )
