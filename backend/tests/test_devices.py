import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_device_lifecycle(client: AsyncClient):
    # 1. Login as Super Admin
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@vaultguard.internal", "password": "AdminSecurePassword123!"},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Org for Device
    create_org = await client.post(
        "/api/v1/organizations",
        json={"name": "Cyber Corp", "contact_email": "ops@cybercorp.io"},
        headers=headers,
    )
    org_id = create_org.json()["data"]["id"]

    # 3. Register Device
    device_payload = {
        "device_id": "SRV-PROD-001",
        "name": "Primary Database Server",
        "os": "Ubuntu 22.04 LTS",
        "organization_id": org_id,
    }
    reg_dev = await client.post("/api/v1/devices", json=device_payload, headers=headers)
    assert reg_dev.status_code == 201
    dev_data = reg_dev.json()["data"]
    assert dev_data["device_id"] == "SRV-PROD-001"
    assert dev_data["status"] == "ONLINE"

    # 4. Get Device
    get_dev = await client.get("/api/v1/devices/SRV-PROD-001", headers=headers)
    assert get_dev.status_code == 200
    assert get_dev.json()["data"]["name"] == "Primary Database Server"

    # 5. Update Device
    update_dev = await client.put(
        "/api/v1/devices/SRV-PROD-001",
        json={"name": "Updated Primary Database Server"},
        headers=headers,
    )
    assert update_dev.status_code == 200
    assert update_dev.json()["data"]["name"] == "Updated Primary Database Server"


async def test_org_admin_enrollment_uses_authenticated_user_and_organization(client: AsyncClient):
    registration = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "device-admin@example.com",
            "password": "StrongPassword123!",
            "full_name": "Device Admin",
            "organization_name": "Device Enrollment Org",
        },
    )
    assert registration.status_code == 201
    registration_data = registration.json()["data"]
    user = registration_data["user"]
    headers = {"Authorization": f"Bearer {registration_data['access_token']}"}

    response = await client.post(
        "/api/v1/devices",
        json={
            "device_id": "AUTO-ENROLLED-DEVICE-001",
            "name": "Windows Computer",
            "os": "Windows",
            "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        },
        headers=headers,
    )

    assert response.status_code == 201
    device = response.json()["data"]
    assert device["organization_id"] == user["organization_id"]
    assert device["user_id"] == user["id"]

