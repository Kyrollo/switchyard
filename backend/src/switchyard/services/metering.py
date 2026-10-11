from __future__ import annotations

import time
from typing import Dict, List, Optional
from ..domain.entities import AuditLogEntry


PRICING_PER_1K_TOKENS: Dict[str, Dict[str, float]] = {
    "local": {"prompt": 0.00005, "completion": 0.00005},
    "ollama": {"prompt": 0.00005, "completion": 0.00005},
    "qwen2.5:0.5b": {"prompt": 0.00005, "completion": 0.00005},
    "llama3.2:latest": {"prompt": 0.00005, "completion": 0.00005},
    "gpt-4o": {"prompt": 0.0025, "completion": 0.010},
    "claude-3-5-sonnet": {"prompt": 0.003, "completion": 0.015},
    "groq-llama-3.3-70b": {"prompt": 0.00059, "completion": 0.00079},
}


class MeteringService:
    """Calculates token pricing, cost accounting, and maintains gateway audit logs."""

    def __init__(self) -> None:
        self._audit_logs: List[AuditLogEntry] = []
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_cost_usd = 0.0

    def estimate_tokens(self, text: str) -> int:
        """Rough token count fallback: approx 4 chars per token."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = PRICING_PER_1K_TOKENS.get(model.lower(), PRICING_PER_1K_TOKENS["local"])
        prompt_cost = (prompt_tokens / 1000.0) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000.0) * pricing["completion"]
        return round(prompt_cost + completion_cost, 6)

    def record_request(
        self,
        virtual_key_id: Optional[str],
        model_requested: str,
        model_resolved: str,
        backend_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cached: bool,
        status_code: int = 200,
    ) -> AuditLogEntry:
        cost = 0.0 if cached else self.calculate_cost(model_resolved, prompt_tokens, completion_tokens)

        entry = AuditLogEntry(
            virtual_key_id=virtual_key_id,
            model_requested=model_requested,
            model_resolved=model_resolved,
            backend_name=backend_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=round(latency_ms, 2),
            cost_usd=cost,
            cached=cached,
            status_code=status_code,
        )

        self._audit_logs.append(entry)
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        self._total_cost_usd += cost

        # Keep max 5000 in memory
        if len(self._audit_logs) > 5000:
            self._audit_logs.pop(0)

        return entry

    def get_summary(self) -> Dict[str, float]:
        total_reqs = len(self._audit_logs)
        avg_latency = (
            sum(e.latency_ms for e in self._audit_logs) / total_reqs if total_reqs > 0 else 0.0
        )
        return {
            "total_requests": float(total_reqs),
            "total_prompt_tokens": float(self._total_prompt_tokens),
            "total_completion_tokens": float(self._total_completion_tokens),
            "total_tokens": float(self._total_prompt_tokens + self._total_completion_tokens),
            "total_cost_usd": round(self._total_cost_usd, 4),
            "avg_latency_ms": round(avg_latency, 1),
        }

    def get_recent_logs(self, limit: int = 50) -> List[AuditLogEntry]:
        return list(reversed(self._audit_logs[-limit:]))


metering_service = MeteringService()
