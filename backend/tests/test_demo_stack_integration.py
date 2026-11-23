"""Opt-in end-to-end test against the local Compose ClamAV and MinIO services."""
import os
import uuid

import pytest
from httpx import AsyncClient

from app.services.recovery.path_validator import path_validator
from app.services.scanning.malware_scanner import ScanStatus, malware_scanner
from app.storage.minio_client import minio_storage


RUN_STACK_INTEGRATION_TESTS = (
    os.getenv("RUN_VAULTGUARD_STACK_INTEGRATION_TESTS") == "1"
)
EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


@pytest.mark.skipif(
    not RUN_STACK_INTEGRATION_TESTS,
    reason="set RUN_VAULTGUARD_STACK_INTEGRATION_TESTS=1 to test local services",
)
@pytest.mark.asyncio
async def test_auth_backup_scan_storage_restore_and_download(
    client: AsyncClient, monkeypatch, tmp_path
):
    assert malware_scanner.scan_bytes(b"clean demo probe", "probe.txt").status == ScanStatus.CLEAN
    assert minio_storage.is_available
    minio_client = minio_storage.client
    assert minio_client is not None

    unique_id = uuid.uuid4().hex
    email = f"vaultguard-demo-{unique_id}@example.com"
    password = f"Demo-{unique_id}-Aa1!"
    registration = await client.post(
        "/api/v1/auth/register/personal",
        json={
            "email": email,
            "password": password,
            "full_name": "VaultGuard Demo Test",
        },
    )
    assert registration.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    device = await client.post(
        "/api/v1/devices",
        headers=headers,
        json={
            "device_id": f"demo-{unique_id}",
            "name": "Demo Test Device",
            "os": "Linux",
        },
    )
    assert device.status_code == 201
    device_id = device.json()["data"]["id"]

    object_name = None
    try:
        clean_payload = b"VaultGuard local end-to-end backup demo."
        upload = await client.post(
            "/api/v1/backups/manual",
            headers=headers,
            data={
                "device_id": device_id,
                "file_path": f"/vaultguard-demo-{unique_id}/notes.txt",
            },
            files={"file": ("notes.txt", clean_payload, "text/plain")},
        )
        assert upload.status_code == 201, upload.text
        version = upload.json()["data"]
        assert version["scan_status"] == ScanStatus.CLEAN.value
        assert version["is_encrypted"] is True
        object_name = version["storage_path"].removeprefix(
            f"{minio_storage.bucket_name}/"
        )
        stored_object = minio_client.stat_object(
            minio_storage.bucket_name, object_name
        )
        assert stored_object.size > 0

        infected_upload = await client.post(
            "/api/v1/backups/manual",
            headers=headers,
            data={
                "device_id": device_id,
                "file_path": f"/vaultguard-demo-{unique_id}/eicar.txt",
            },
            files={"file": ("eicar.txt", EICAR, "application/octet-stream")},
        )
        assert infected_upload.status_code == 422
        assert infected_upload.json()["error"]["code"] == "MALWARE_DETECTED"

        snapshots = await client.get(
            "/api/v1/backups?owner_scope=mine", headers=headers
        )
        assert snapshots.status_code == 200
        assert snapshots.json()["data"]["total"] == 1

        monkeypatch.setattr(path_validator, "STAGING_ROOT", str(tmp_path / "staging"))
        restore_dir = tmp_path / "restored"
        restore = await client.post(
            "/api/v1/recovery/restore/single",
            headers=headers,
            json={
                "file_version_id": version["id"],
                "destination_type": "CUSTOM_SAFE_DIR",
                "destination_path": str(restore_dir),
            },
        )
        assert restore.status_code == 201, restore.text
        restore_data = restore.json()["data"]
        assert restore_data["status"] == "COMPLETED"
        assert (restore_dir / "notes.txt").read_bytes() == clean_payload

        details = await client.get(
            f"/api/v1/recovery/jobs/{restore_data['id']}", headers=headers
        )
        assert details.status_code == 200
        item_id = details.json()["data"]["items"][0]["id"]
        download = await client.get(
            f"/api/v1/recovery/jobs/{restore_data['id']}/items/{item_id}/download",
            headers=headers,
        )
        assert download.status_code == 200
        assert download.content == clean_payload
    finally:
        if object_name is not None:
            minio_client.remove_object(minio_storage.bucket_name, object_name)
