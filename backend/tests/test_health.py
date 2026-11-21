import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "OPERATIONAL"


async def test_health_endpoints(client: AsyncClient):
    # Infrastructure status is not public: anonymous requests must be rejected.
    anonymous = await client.get("/api/v1/health")
    assert anonymous.status_code in (401, 403)

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@vaultguard.internal", "password": "AdminSecurePassword123!"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]

    response = await client.get("/api/v1/health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "services" in data["data"]

