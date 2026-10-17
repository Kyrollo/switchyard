from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple
import httpx
from ..core.errors import UpstreamUnavailableException
from ..core.telemetry import logger
from ..domain.entities import (
    BackendNode,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatChoice,
    ChatMessage,
    ProviderType,
    RoutingPolicy,
    RoutingStrategy,
    UsageInfo,
)


class RoutingEngine:
    """Dynamic routing engine with circuit breakers, model aliases, and multi-provider failover."""

    def __init__(self) -> None:
        self.backends: Dict[str, BackendNode] = {}
        self.policies: Dict[str, RoutingPolicy] = {}
        self._init_default_backends_and_policies()

    def _init_default_backends_and_policies(self) -> None:
        # 1. Primary: Local Ollama on RTX A5000 GPU
        local_node = BackendNode(
            id="node-local-gpu",
            name="Local RTX A5000 (Ollama)",
            provider=ProviderType.OLLAMA,
            base_url="http://127.0.0.1:11434/v1",
            models=["qwen2.5:0.5b", "llama3.2:latest", "mistral:latest"],
            weight=100,
            latency_p95_ms=8.2,
            is_healthy=True,
        )
        self.backends[local_node.id] = local_node

        # 2. Cloud Fallback 1: Groq Fast Cloud
        groq_node = BackendNode(
            id="node-cloud-groq",
            name="Groq Cloud Llama-3.3 (Fallback 1)",
            provider=ProviderType.GROQ,
            base_url="https://api.groq.com/openai/v1",
            api_key=None,
            models=["llama-3.3-70b-versatile"],
            weight=80,
            latency_p95_ms=18.5,
            is_healthy=True,
        )
        self.backends[groq_node.id] = groq_node

        # 3. Cloud Fallback 2: OpenAI
        openai_node = BackendNode(
            id="node-cloud-openai",
            name="OpenAI GPT-4o (Fallback 2)",
            provider=ProviderType.OPENAI,
            base_url="https://api.openai.com/v1",
            api_key=None,
            models=["gpt-4o", "gpt-4o-mini"],
            weight=50,
            latency_p95_ms=45.0,
            is_healthy=True,
        )
        self.backends[openai_node.id] = openai_node

        # Default policy: company-default alias routes to Local GPU primary with cloud fallbacks
        default_policy = RoutingPolicy(
            id="pol-company-default",
            name="Enterprise Default Route",
            model_alias="company-default",
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
            primary_backend_ids=[local_node.id],
            fallback_backend_ids=[groq_node.id, openai_node.id],
            is_active=True,
        )
        self.policies[default_policy.model_alias] = default_policy

    def resolve_backend_chain(self, requested_model: str) -> List[Tuple[BackendNode, str]]:
        """Returns ordered list of (BackendNode, model_name_for_backend)."""
        now = time.time()
        chain: List[Tuple[BackendNode, str]] = []

        # If alias matched in policies
        if requested_model in self.policies:
            policy = self.policies[requested_model]
            all_ids = policy.primary_backend_ids + policy.fallback_backend_ids
            for node_id in all_ids:
                if node_id in self.backends:
                    node = self.backends[node_id]
                    # Check circuit breaker
                    if node.circuit_open and (now - node.last_checked < 30.0):
                        continue  # Skip tripped circuit
                    target_model = node.models[0] if node.models else "qwen2.5:0.5b"
                    chain.append((node, target_model))
            if chain:
                return chain

        # Direct model name requested: check if any backend has it
        for node in self.backends.values():
            if node.circuit_open and (now - node.last_checked < 30.0):
                continue
            if requested_model in node.models or "*" in node.models or requested_model == "default":
                chain.append((node, requested_model if requested_model != "default" else node.models[0]))

        # Fallback to local GPU node if chain is empty
        if not chain and "node-local-gpu" in self.backends:
            local = self.backends["node-local-gpu"]
            chain.append((local, "qwen2.5:0.5b"))

        return chain

    def record_node_success(self, node: BackendNode, duration_ms: float) -> None:
        node.is_healthy = True
        node.consecutive_failures = 0
        node.circuit_open = False
        node.last_checked = time.time()
        # Smooth EMA for latency
        node.latency_p95_ms = round(node.latency_p95_ms * 0.8 + duration_ms * 0.2, 1)

    def record_node_failure(self, node: BackendNode, error_msg: str) -> None:
        node.consecutive_failures += 1
        node.last_checked = time.time()
        logger.warning(
            "backend_node_failure",
            node_id=node.id,
            name=node.name,
            failures=node.consecutive_failures,
            error=error_msg,
        )
        if node.consecutive_failures >= 3:
            node.circuit_open = True
            node.is_healthy = False
            logger.error("circuit_breaker_tripped", node_id=node.id, name=node.name)

    async def execute_chat_completion(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        chain = self.resolve_backend_chain(request.model)
        if not chain:
            raise UpstreamUnavailableException(
                f"No available healthy backend found for model '{request.model}'"
            )

        last_error = "Unknown error"

        for node, target_model in chain:
            start_time = time.perf_counter()
            payload = {
                "model": target_model,
                "messages": [m.model_dump() for m in request.messages],
                "temperature": request.temperature,
                "stream": False,
            }
            payload["max_tokens"] = request.max_tokens if request.max_tokens else 2048

            headers = {"Content-Type": "application/json"}
            if node.api_key:
                headers["Authorization"] = f"Bearer {node.api_key}"

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{node.base_url.rstrip('/')}/chat/completions",
                        json=payload,
                        headers=headers,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    self.record_node_success(node, duration_ms)

                    # Normalize OpenAI response
                    choice_data = data.get("choices", [{}])[0]
                    msg_data = choice_data.get("message", {})
                    usage_data = data.get("usage", {})

                    return ChatCompletionResponse(
                        id=data.get("id", f"chatcmpl-{int(time.time())}"),
                        model=target_model,
                        choices=[
                            ChatChoice(
                                index=0,
                                message=ChatMessage(
                                    role=msg_data.get("role", "assistant"),
                                    content=msg_data.get("content", ""),
                                ),
                                finish_reason=choice_data.get("finish_reason", "stop"),
                            )
                        ],
                        usage=UsageInfo(
                            prompt_tokens=usage_data.get("prompt_tokens", len(str(request.messages)) // 4),
                            completion_tokens=usage_data.get("completion_tokens", len(msg_data.get("content", "")) // 4),
                            total_tokens=usage_data.get("total_tokens", 0),
                        ),
                        backend_id=node.id,
                        cached=False,
                        latency_ms=round(duration_ms, 2),
                    )
                else:
                    err_text = f"HTTP {resp.status_code}: {resp.text[:100]}"
                    self.record_node_failure(node, err_text)
                    last_error = err_text

            except Exception as exc:
                err_text = str(exc)
                self.record_node_failure(node, err_text)
                last_error = err_text

        # If all in chain failed
        raise UpstreamUnavailableException(
            f"All backend providers in routing chain failed for '{request.model}'. Last error: {last_error}"
        )


routing_engine = RoutingEngine()
