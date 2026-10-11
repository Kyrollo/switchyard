import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_models_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    model_ids = [m["id"] for m in data["data"]]
    assert "company-default" in model_ids


@pytest.mark.asyncio
async def test_admin_dashboard_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "gpu" in data
    assert "backends" in data
    assert "virtual_keys" in data


@pytest.mark.asyncio
async def test_admin_key_lifecycle(client: AsyncClient) -> None:
    # 1. Create key
    create_resp = await client.post(
        "/api/v1/admin/keys",
        json={"name": "Integration Test Key", "rpm_limit": 500, "tpm_limit": 80000},
    )
    assert create_resp.status_code == 201
    key_data = create_resp.json()
    assert "api_key" in key_data
    key_id = key_data["key"]["id"]

    # 2. List keys
    list_resp = await client.get("/api/v1/admin/keys")
    assert list_resp.status_code == 200
    all_keys = list_resp.json()
    assert any(k["id"] == key_id for k in all_keys)

    # 3. Revoke key
    del_resp = await client.delete(f"/api/v1/admin/keys/{key_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["revoked"] is True


@pytest.mark.asyncio
async def test_chat_completions_gateway_flow(client: AsyncClient) -> None:
    # Test chat completion through the gateway using the live warm local Ollama model
    response = await client.post(
        "/api/v1/chat/completions",
        json={
            "model": "qwen2.5:0.5b",
            "messages": [{"role": "user", "content": "Respond with the single word: OK"}],
            "max_tokens": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert len(data["choices"][0]["message"]["content"]) > 0
    assert data["cached"] is False

    # Second call with identical payload must be a semantic/exact cache HIT
    cache_response = await client.post(
        "/api/v1/chat/completions",
        json={
            "model": "qwen2.5:0.5b",
            "messages": [{"role": "user", "content": "Respond with the single word: OK"}],
            "max_tokens": 10,
        },
    )
    assert cache_response.status_code == 200
    cached_data = cache_response.json()
    assert cached_data["cached"] is True
