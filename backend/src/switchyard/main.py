from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.health import router as health_router
from .api.v1.router import api_v1_router
from .core.config import settings
from .core.errors import AppException, app_exception_handler
from .core.telemetry import logger, telemetry_middleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("app_starting", app="Switchyard", version="1.0.0", port=settings.PORT)
    yield
    logger.info("app_stopping", app="Switchyard")


app = FastAPI(
    title="Switchyard API",
    description="Private LLM Gateway: unified OpenAI-compatible routing over local and cloud models with quotas, virtual keys, and audit logging",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)

# Middlewares
app.middleware("http")(telemetry_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root level health routes for k8s/docker
app.include_router(health_router)

# Versioned API routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
