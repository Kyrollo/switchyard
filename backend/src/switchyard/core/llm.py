from __future__ import annotations

import time
from typing import Any, Type, TypeVar
import httpx
import instructor
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter
from .config import settings
from .errors import UpstreamUnavailableException
from .telemetry import LLM_CALL_DURATION_SECONDS, LLM_CALLS_TOTAL, logger

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Provider-agnostic LLM client. Ollama local by default; any OpenAI-compatible endpoint via env.
    
    Strict production policy: live inference only. If upstream fails, raises UpstreamUnavailableException
    which produces an RFC 7807 503 response. NEVER produces synthetic fallback data.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        default_model: str | None = None,
    ) -> None:
        self.base_url = base_url or settings.LLM_BASE_URL
        self.api_key = api_key or settings.LLM_API_KEY
        self.default_model = default_model or settings.LLM_MODEL
        self._raw_client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=0,
        )
        self._structured_client = instructor.from_openai(
            self._raw_client,
            mode=instructor.Mode.JSON,
        )

    @retry(
        stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
        wait=wait_exponential_jitter(initial=0.5, max=8.0),
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError, RateLimitError)),
        reraise=True,
    )
    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        target_model = model or self.default_model
        start_time = time.perf_counter()

        try:
            response = await self._raw_client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                **kwargs,
            )
            duration = time.perf_counter() - start_time
            LLM_CALLS_TOTAL.labels(model=target_model, status="success").inc()
            LLM_CALL_DURATION_SECONDS.labels(model=target_model).observe(duration)
            content = response.choices[0].message.content
            return content or ""
        except (APIConnectionError, APITimeoutError, httpx.ConnectError) as exc:
            duration = time.perf_counter() - start_time
            LLM_CALLS_TOTAL.labels(model=target_model, status="error").inc()
            logger.error("llm_upstream_unavailable", model=target_model, error=str(exc))
            raise UpstreamUnavailableException(
                f"LLM upstream service at {self.base_url} is unavailable: {exc}"
            ) from exc

    @retry(
        stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
        wait=wait_exponential_jitter(initial=0.5, max=8.0),
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError, RateLimitError)),
        reraise=True,
    )
    async def structured_complete(
        self,
        messages: list[dict[str, Any]],
        response_model: Type[T],
        *,
        model: str | None = None,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> T:
        target_model = model or self.default_model
        start_time = time.perf_counter()

        try:
            result = await self._structured_client.chat.completions.create(
                model=target_model,
                messages=messages,
                response_model=response_model,
                temperature=temperature,
                **kwargs,
            )
            duration = time.perf_counter() - start_time
            LLM_CALLS_TOTAL.labels(model=target_model, status="success").inc()
            LLM_CALL_DURATION_SECONDS.labels(model=target_model).observe(duration)
            return result
        except (APIConnectionError, APITimeoutError, httpx.ConnectError) as exc:
            duration = time.perf_counter() - start_time
            LLM_CALLS_TOTAL.labels(model=target_model, status="error").inc()
            logger.error("llm_upstream_unavailable", model=target_model, error=str(exc))
            raise UpstreamUnavailableException(
                f"LLM upstream service at {self.base_url} is unavailable: {exc}"
            ) from exc


llm_client = LLMClient()
