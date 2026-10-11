from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    OLLAMA = "ollama"
    VLLM = "vllm"
    OPENAI = "openai"
    GROQ = "groq"
    ANTHROPIC = "anthropic"


class RoutingStrategy(str, Enum):
    LOWEST_LATENCY = "lowest_latency"
    CHEAPEST = "cheapest"
    ROUND_ROBIN = "round_robin"
    PRIORITY_FAILOVER = "priority_failover"


class BackendNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    provider: ProviderType
    base_url: str
    api_key: Optional[str] = None
    models: List[str] = Field(default_factory=list)
    weight: int = 100
    latency_p95_ms: float = 10.0
    is_healthy: bool = True
    consecutive_failures: int = 0
    circuit_open: bool = False
    last_checked: float = Field(default_factory=time.time)


class RoutingPolicy(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    model_alias: str  # e.g. "company-default"
    strategy: RoutingStrategy = RoutingStrategy.PRIORITY_FAILOVER
    primary_backend_ids: List[str] = Field(default_factory=list)
    fallback_backend_ids: List[str] = Field(default_factory=list)
    is_active: bool = True


class VirtualKey(BaseModel):
    id: str = Field(default_factory=lambda: f"key_{uuid.uuid4().hex[:12]}")
    name: str
    key_prefix: str
    key_hash: str
    rpm_limit: int = 600
    tpm_limit: int = 100000
    monthly_budget_usd: float = 500.0
    budget_spent_usd: float = 0.0
    allowed_models: List[str] = Field(default_factory=lambda: ["*"])
    is_active: bool = True
    created_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    user: Optional[str] = None


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatChoice]
    usage: UsageInfo
    backend_id: Optional[str] = None
    cached: bool = False
    latency_ms: float = 0.0


class GPUInfo(BaseModel):
    name: str
    vram_total_mb: float
    vram_used_mb: float
    vram_free_mb: float
    utilization_pct: float
    temperature_c: Optional[float] = None


class AuditLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = Field(default_factory=time.time)
    virtual_key_id: Optional[str] = None
    model_requested: str
    model_resolved: str
    backend_name: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cost_usd: float
    cached: bool
    status_code: int
