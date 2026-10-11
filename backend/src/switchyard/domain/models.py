from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class ServiceHealthStatus(str, Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"


class SystemInfo(BaseModel):
    app_name: str
    version: str
    environment: str
    status: ServiceHealthStatus
    llm_backend: str
