import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_login_flow(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/token",
        json={"email": "engineer@antigravity.io", "password": "securepassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
