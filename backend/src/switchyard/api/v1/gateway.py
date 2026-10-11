from __future__ import annotations

import time
from typing import Annotated, Any, Dict, List
from fastapi import APIRouter, Header, HTTPException, status
from ...core.errors import AppException, UnauthorizedException
from ...core.security import hash_api_key
from ...domain.entities import (
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from ...services.key_manager import key_manager
from ...services.metering import metering_service
from ...services.rate_limiter import rate_limiter
from ...services.routing_engine import routing_engine
from ...services.semantic_cache import semantic_cache

router = APIRouter(tags=["gateway"])


def authenticate_virtual_key(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        # For development / direct access, default to primary admin key
        return "key_default_admin"

    raw_token = authorization.split(" ")[1]
    key_hash = hash_api_key(raw_token)
    vkey = key_manager.get_by_hash(key_hash)

    if not vkey or not vkey.is_active:
        raise UnauthorizedException("Invalid or revoked Virtual API Key")

    return vkey.id


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> ChatCompletionResponse:
    key_id = authenticate_virtual_key(authorization)
    vkey = key_manager._keys.get(key_id)

    # 1. Model allowlist check
    if vkey and "*" not in vkey.allowed_models:
        if request.model not in vkey.allowed_models:
            raise AppException(
                f"Model '{request.model}' is not allowed for this Virtual Key",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    # 2. Rate limit token bucket check
    if vkey:
        prompt_text = " ".join(m.content for m in request.messages)
        est_tokens = metering_service.estimate_tokens(prompt_text)
        rate_limiter.check_and_consume(
            key_id=vkey.id,
            rpm_limit=vkey.rpm_limit,
            tpm_limit=vkey.tpm_limit,
            estimated_tokens=est_tokens,
        )

    # 3. Check semantic & exact cache
    cached_response = semantic_cache.get(request.model, request.messages)
    if cached_response:
        metering_service.record_request(
            virtual_key_id=key_id,
            model_requested=request.model,
            model_resolved=cached_response.model,
            backend_name="semantic-cache",
            prompt_tokens=cached_response.usage.prompt_tokens,
            completion_tokens=cached_response.usage.completion_tokens,
            latency_ms=1.2,
            cached=True,
            status_code=200,
        )
        return cached_response

    # 4. Real routing execution across backends
    start_time = time.perf_counter()
    response = await routing_engine.execute_chat_completion(request)
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    # 5. Put in semantic cache
    semantic_cache.put(request.model, request.messages, response)

    # 6. Metering & Cost tracking
    entry = metering_service.record_request(
        virtual_key_id=key_id,
        model_requested=request.model,
        model_resolved=response.model,
        backend_name=response.backend_id or "local-gpu",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        latency_ms=duration_ms,
        cached=False,
        status_code=200,
    )
    if vkey:
        key_manager.record_spend(vkey.id, entry.cost_usd)

    return response


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """OpenAI-compatible models catalog listing local and routing aliases."""
    available = [
        {"id": "company-default", "object": "model", "owned_by": "switchyard-gateway", "type": "alias"},
        {"id": "qwen2.5:0.5b", "object": "model", "owned_by": "local-ollama-gpu", "type": "local"},
        {"id": "llama-3.3-70b-versatile", "object": "model", "owned_by": "groq-cloud", "type": "fallback"},
        {"id": "gpt-4o", "object": "model", "owned_by": "openai", "type": "fallback"},
    ]
    return {"object": "list", "data": available}
