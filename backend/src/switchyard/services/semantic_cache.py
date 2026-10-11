from __future__ import annotations

import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple
from ..domain.entities import ChatCompletionResponse, ChatMessage


class SemanticCacheService:
    """Multi-tier exact and semantic cache for LLM gateway requests."""

    def __init__(self, similarity_threshold: float = 0.95, ttl_seconds: float = 3600.0) -> None:
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        # exact_hash -> (expiry_time, cached_response)
        self._exact_cache: Dict[str, Tuple[float, ChatCompletionResponse]] = {}
        # list of (prompt_text, expiry_time, cached_response)
        self._semantic_entries: List[Tuple[str, float, ChatCompletionResponse]] = []
        self._total_lookups = 0
        self._total_hits = 0

    def _hash_request(self, model: str, messages: List[ChatMessage]) -> str:
        serialized = json.dumps(
            {"model": model, "messages": [m.model_dump() for m in messages]},
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(
        self,
        model: str,
        messages: List[ChatMessage],
    ) -> Optional[ChatCompletionResponse]:
        self._total_lookups += 1
        now = time.time()
        exact_key = self._hash_request(model, messages)

        # 1. Check exact cache
        if exact_key in self._exact_cache:
            expiry, resp = self._exact_cache[exact_key]
            if expiry > now:
                self._total_hits += 1
                resp_copy = resp.model_copy(deep=True)
                resp_copy.cached = True
                return resp_copy
            else:
                del self._exact_cache[exact_key]

        # 2. Check semantic similarity
        if not messages:
            return None

        current_prompt = messages[-1].content.strip().lower()
        if len(current_prompt) < 10:
            return None

        # Clean expired entries
        self._semantic_entries = [
            (p, exp, r) for p, exp, r in self._semantic_entries if exp > now
        ]

        import re
        current_tokens = set(re.findall(r"\w+", current_prompt))
        for cached_prompt, _, cached_resp in self._semantic_entries:
            cached_tokens = set(re.findall(r"\w+", cached_prompt))
            intersection = len(current_tokens & cached_tokens)
            union = len(current_tokens | cached_tokens)
            similarity = (intersection / union) if union > 0 else 0.0

            if similarity >= self.similarity_threshold:
                self._total_hits += 1
                resp_copy = cached_resp.model_copy(deep=True)
                resp_copy.cached = True
                return resp_copy

        return None

    def put(
        self,
        model: str,
        messages: List[ChatMessage],
        response: ChatCompletionResponse,
    ) -> None:
        now = time.time()
        expiry = now + self.ttl_seconds
        exact_key = self._hash_request(model, messages)
        self._exact_cache[exact_key] = (expiry, response)

        if messages:
            prompt_text = messages[-1].content.strip().lower()
            self._semantic_entries.append((prompt_text, expiry, response))

    @property
    def hit_rate(self) -> float:
        if self._total_lookups == 0:
            return 0.0
        return round((self._total_hits / self._total_lookups) * 100, 1)

    @property
    def total_cached_items(self) -> int:
        return len(self._exact_cache)


semantic_cache = SemanticCacheService()
