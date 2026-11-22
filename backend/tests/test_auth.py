import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_auth_workflow(client: AsyncClient):
    # 1. Register
    register_payload = {
        "email": "corp_admin@acmesec.com",
        "password": "StrongPassword123!",
        "full_name": "ACME Admin",
        "organization_name": "ACME Corporation",
    }
    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["success"] is True
    assert "access_token" in reg_data["data"]
    assert "refresh_token" in reg_data["data"]
    access_token = reg_data["data"]["access_token"]
    refresh_token = reg_data["data"]["refresh_token"]

    # 2. Access /me
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["success"] is True
    assert me_data["data"]["email"] == "corp_admin@acmesec.com"
    assert me_data["data"]["role"]["name"] == "ADMIN"

    # 3. Login
    login_payload = {
        "email": "corp_admin@acmesec.com",
        "password": "StrongPassword123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["success"] is True
    assert "access_token" in login_data["data"]

    # 4. Token Refresh
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    refresh_data = refresh_res.json()
    assert refresh_data["success"] is True
    assert "access_token" in refresh_data["data"]
    new_refresh = refresh_data["data"]["refresh_token"]

    # 5. Logout
    logout_res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_refresh},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_res.status_code == 200


async def test_invalid_login(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@test.com", "password": "wrongpassword"},
    )
    assert res.status_code == 401
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"


async def test_swagger_oauth2_login(client: AsyncClient):
    invalid_json_res = await client.post(
        "/api/v1/auth/login",
        content="{",
        headers={"Content-Type": "application/json"},
    )
    assert invalid_json_res.status_code == 422
    validation_error = invalid_json_res.json()["error"]
    assert validation_error["code"] == "VALIDATION_ERROR"
    assert validation_error["details"][0]["type"] == "json_invalid"

    schema_res = await client.get("/openapi.json")
    assert schema_res.status_code == 200
    schema = schema_res.json()
    oauth_scheme = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert oauth_scheme["flows"]["password"]["tokenUrl"] == "/api/v1/auth/login"
    login_content = schema["paths"]["/api/v1/auth/login"]["post"]["requestBody"]["content"]
    assert "email" in login_content["application/json"]["schema"]["properties"]
    assert "username" in login_content["application/x-www-form-urlencoded"]["schema"]["properties"]

    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vaultguard.internal", "password": "AdminSecurePassword123!"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert "data" not in token_data

    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == "admin@vaultguard.internal"

