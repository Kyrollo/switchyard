from __future__ import annotations

from fastapi import APIRouter
from .health import router as health_router
from .auth import router as auth_router
from .gateway import router as gateway_router
from .admin import router as admin_router
from .files import router as files_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(gateway_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(files_router)


@api_v1_router.get("/info", tags=["info"])
async def get_system_info() -> dict[str, str]:
    return {
        "name": "Switchyard",
        "slug": "switchyard",
        "archetype": "Infra admin console",
        "version": "1.0.0",
        "description": "Private LLM Gateway: unified OpenAI-compatible routing over local and cloud models with quotas, virtual keys, and audit logging",
    }
