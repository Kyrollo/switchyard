import pytest
from src.switchyard.domain.entities import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatChoice,
    UsageInfo,
    ProviderType,
)
from src.switchyard.services.rate_limiter import TokenBucketRateLimiter, RateLimitExceededException
from src.switchyard.services.semantic_cache import SemanticCacheService
from src.switchyard.services.metering import MeteringService
from src.switchyard.services.key_manager import VirtualKeyManager
from src.switchyard.services.routing_engine import RoutingEngine


def test_rate_limiter_sliding_window() -> None:
    limiter = TokenBucketRateLimiter()
    key_id = "test_key_1"
    rpm_limit = 3
    tpm_limit = 1000

    # First 3 should succeed
    allowed, rpm, tpm = limiter.check_and_consume(key_id, rpm_limit, tpm_limit, estimated_tokens=10)
    assert allowed is True
    assert rpm == 1

    limiter.check_and_consume(key_id, rpm_limit, tpm_limit, estimated_tokens=10)
    limiter.check_and_consume(key_id, rpm_limit, tpm_limit, estimated_tokens=10)

    # 4th should raise 429
    with pytest.raises(RateLimitExceededException):
        limiter.check_and_consume(key_id, rpm_limit, tpm_limit, estimated_tokens=10)


def test_semantic_cache_exact_and_similarity() -> None:
    cache = SemanticCacheService(similarity_threshold=0.8, ttl_seconds=60.0)
    messages = [ChatMessage(role="user", content="How do I configure routing policies in Switchyard?")]
    model = "company-default"

    # Miss initially
    assert cache.get(model, messages) is None

    # Put response
    resp = ChatCompletionResponse(
        model=model,
        choices=[ChatChoice(index=0, message=ChatMessage(role="assistant", content="Use the /admin/routes API."))],
        usage=UsageInfo(prompt_tokens=10, completion_tokens=10, total_tokens=20),
    )
    cache.put(model, messages, resp)

    # Exact hit
    hit = cache.get(model, messages)
    assert hit is not None
    assert hit.cached is True
    assert hit.choices[0].message.content == "Use the /admin/routes API."

    # Semantic hit (very similar wording)
    similar_messages = [ChatMessage(role="user", content="How do I configure routing policies in Switchyard platform?")]
    sem_hit = cache.get(model, similar_messages)
    assert sem_hit is not None
    assert sem_hit.cached is True


def test_metering_and_pricing() -> None:
    metering = MeteringService()
    cost = metering.calculate_cost("qwen2.5:0.5b", prompt_tokens=1000, completion_tokens=1000)
    assert cost > 0.0

    entry = metering.record_request(
        virtual_key_id="key_test",
        model_requested="company-default",
        model_resolved="qwen2.5:0.5b",
        backend_name="local-gpu",
        prompt_tokens=50,
        completion_tokens=50,
        latency_ms=12.5,
        cached=False,
    )
    assert entry.cost_usd > 0.0

    summary = metering.get_summary()
    assert summary["total_requests"] >= 1


def test_key_manager_creation_and_hash() -> None:
    km = VirtualKeyManager()
    key, raw_token = km.create_key("Dev Test Key", rpm_limit=300, tpm_limit=50000)
    assert raw_token.startswith("sk_live_")
    assert key.rpm_limit == 300
    assert km.get_by_hash(key.key_hash) is not None

    km.revoke_key(key.id)
    assert key.is_active is False
