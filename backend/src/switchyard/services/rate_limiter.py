from __future__ import annotations

import time
from typing import Dict, List, Tuple
from ..core.errors import AppException


class RateLimitExceededException(AppException):
    status_code = 429
    title = "Rate Limit Exceeded"
    type_uri = "https://errors.antigravity.io/rate-limit-exceeded"
    code = "RATE_LIMIT_EXCEEDED"


class TokenBucketRateLimiter:
    """Sliding-window token bucket limiter for RPM and TPM."""

    def __init__(self) -> None:
        # key_id -> list of timestamp floats
        self._request_history: Dict[str, List[float]] = {}
        # key_id -> list of (timestamp float, token_count int)
        self._token_history: Dict[str, List[Tuple[float, int]]] = {}

    def check_and_consume(
        self,
        key_id: str,
        rpm_limit: int,
        tpm_limit: int,
        estimated_tokens: int = 50,
    ) -> Tuple[bool, int, int]:
        now = time.time()
        window_start = now - 60.0

        # Clean old request timestamps
        if key_id not in self._request_history:
            self._request_history[key_id] = []
        self._request_history[key_id] = [
            ts for ts in self._request_history[key_id] if ts > window_start
        ]

        # Clean old token timestamps
        if key_id not in self._token_history:
            self._token_history[key_id] = []
        self._token_history[key_id] = [
            (ts, tok) for ts, tok in self._token_history[key_id] if ts > window_start
        ]

        current_rpm = len(self._request_history[key_id])
        current_tpm = sum(tok for _, tok in self._token_history[key_id])

        if current_rpm >= rpm_limit:
            raise RateLimitExceededException(
                f"Virtual key {key_id} exceeded RPM limit ({current_rpm}/{rpm_limit} req/min)"
            )

        if current_tpm + estimated_tokens > tpm_limit:
            raise RateLimitExceededException(
                f"Virtual key {key_id} exceeded TPM limit ({current_tpm + estimated_tokens}/{tpm_limit} tok/min)"
            )

        # Record usage
        self._request_history[key_id].append(now)
        self._token_history[key_id].append((now, estimated_tokens))

        return True, current_rpm + 1, current_tpm + estimated_tokens

    def get_usage(self, key_id: str) -> Tuple[int, int]:
        now = time.time()
        window_start = now - 60.0
        reqs = [ts for ts in self._request_history.get(key_id, []) if ts > window_start]
        tokens = sum(tok for ts, tok in self._token_history.get(key_id, []) if ts > window_start)
        return len(reqs), tokens


rate_limiter = TokenBucketRateLimiter()
