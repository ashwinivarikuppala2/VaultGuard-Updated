import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_organization_crud(client: AsyncClient):
    # Login as seeded Super Admin
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@vaultguard.internal", "password": "AdminSecurePassword123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Org
    org_payload = {
        "name": "Global Defense Systems",
        "slug": "global-defense",
        "contact_email": "security@gds.example.com",
        "max_devices": 100,
        "storage_quota_bytes": 107374182400,
    }
    create_res = await client.post("/api/v1/organizations", json=org_payload, headers=headers)
    assert create_res.status_code == 201
    org_data = create_res.json()["data"]
    org_id = org_data["id"]
    assert org_data["name"] == "Global Defense Systems"

    # 2. Get Org
    get_res = await client.get(f"/api/v1/organizations/{org_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["slug"] == "global-defense"

    # 3. Update Org
    update_res = await client.put(
        f"/api/v1/organizations/{org_id}",
        json={"max_devices": 150},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["max_devices"] == 150

    # 4. List Orgs
    list_res = await client.get("/api/v1/organizations", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["data"]["total"] >= 1

