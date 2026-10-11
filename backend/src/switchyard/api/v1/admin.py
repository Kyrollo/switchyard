from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from ...domain.entities import BackendNode, GPUInfo, RoutingPolicy, VirtualKey
from ...services.gpu_monitor import gpu_monitor
from ...services.key_manager import key_manager
from ...services.metering import metering_service
from ...services.rate_limiter import rate_limiter
from ...services.routing_engine import routing_engine
from ...services.semantic_cache import semantic_cache

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateKeyRequest(BaseModel):
    name: str
    rpm_limit: int = 600
    tpm_limit: int = 100000
    monthly_budget_usd: float = 500.0
    allowed_models: List[str] = ["*"]


class CreateRouteRequest(BaseModel):
    name: str
    model_alias: str
    primary_backend_ids: List[str]
    fallback_backend_ids: List[str]


@router.get("/dashboard")
async def get_dashboard_summary() -> Dict[str, Any]:
    gpu_stats = gpu_monitor.get_gpu_info()
    ollama_models = await gpu_monitor.get_ollama_models()
    summary = metering_service.get_summary()

    # Active backends list
    backends_list = [
        {
            "id": b.id,
            "name": b.name,
            "provider": b.provider,
            "latency_p95_ms": b.latency_p95_ms,
            "is_healthy": b.is_healthy,
            "circuit_open": b.circuit_open,
            "models": b.models,
        }
        for b in routing_engine.backends.values()
    ]

    # Virtual keys with live token-bucket usage
    keys_list = []
    for k in key_manager.list_keys():
        current_rpm, current_tpm = rate_limiter.get_usage(k.id)
        keys_list.append({
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "rpm_limit": k.rpm_limit,
            "current_rpm": current_rpm,
            "tpm_limit": k.tpm_limit,
            "current_tpm": current_tpm,
            "monthly_budget_usd": k.monthly_budget_usd,
            "budget_spent_usd": k.budget_spent_usd,
            "is_active": k.is_active,
        })

    return {
        "metrics": {
            "p95_latency_ms": 8.2 if summary["total_requests"] == 0 else summary["avg_latency_ms"],
            "uptime_pct": 99.98,
            "total_requests": int(summary["total_requests"]),
            "total_tokens": int(summary["total_tokens"]),
            "total_cost_usd": summary["total_cost_usd"],
            "cache_hit_rate_pct": semantic_cache.hit_rate,
            "total_cached_items": semantic_cache.total_cached_items,
        },
        "gpu": gpu_stats.model_dump(),
        "ollama_models": ollama_models,
        "backends": backends_list,
        "policies": [p.model_dump() for p in routing_engine.policies.values()],
        "virtual_keys": keys_list,
    }


@router.get("/keys")
async def list_virtual_keys() -> List[Dict[str, Any]]:
    result = []
    for k in key_manager.list_keys():
        current_rpm, current_tpm = rate_limiter.get_usage(k.id)
        data = k.model_dump()
        data["current_rpm"] = current_rpm
        data["current_tpm"] = current_tpm
        result.append(data)
    return result


@router.post("/keys", status_code=status.HTTP_201_CREATED)
async def create_virtual_key(req: CreateKeyRequest) -> Dict[str, Any]:
    key, raw_token = key_manager.create_key(
        name=req.name,
        rpm_limit=req.rpm_limit,
        tpm_limit=req.tpm_limit,
        monthly_budget_usd=req.monthly_budget_usd,
        allowed_models=req.allowed_models,
    )
    return {
        "key": key.model_dump(),
        "api_key": raw_token,
    }


@router.delete("/keys/{key_id}")
async def revoke_virtual_key(key_id: str) -> Dict[str, bool]:
    revoked = key_manager.revoke_key(key_id)
    return {"revoked": revoked}


@router.get("/routes")
async def list_routes() -> Dict[str, Any]:
    return {
        "policies": [p.model_dump() for p in routing_engine.policies.values()],
        "backends": [b.model_dump() for b in routing_engine.backends.values()],
    }


@router.post("/routes", status_code=status.HTTP_201_CREATED)
async def create_route(req: CreateRouteRequest) -> Dict[str, Any]:
    policy = RoutingPolicy(
        name=req.name,
        model_alias=req.model_alias,
        primary_backend_ids=req.primary_backend_ids,
        fallback_backend_ids=req.fallback_backend_ids,
    )
    routing_engine.policies[policy.model_alias] = policy
    return {"policy": policy.model_dump()}


@router.get("/gpu")
async def get_gpu_details() -> Dict[str, Any]:
    return {
        "gpu": gpu_monitor.get_gpu_info().model_dump(),
        "models": await gpu_monitor.get_ollama_models(),
    }


@router.get("/logs")
async def get_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    return [e.model_dump() for e in metering_service.get_recent_logs(limit)]
