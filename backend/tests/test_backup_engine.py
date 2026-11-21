import base64
import os
import uuid
import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient

from app.core.compression import compression_service
from app.core.encryption import encryption_service
from app.services.backup_service import BackupService
from app.services.scanning.malware_scanner import ScanResult, ScanStatus
from app.storage.minio_client import minio_storage

# ==================== 1. Compression Tests ====================
def test_compression_roundtrip():
    original = b"VaultGuard Secure Cloud Backup Engine - Compression Test Data " * 50
    compressed, orig_size, comp_size, ratio = compression_service.compress(original)

    assert len(original) == orig_size
    assert comp_size < orig_size
    assert ratio < 1.0

    decompressed = compression_service.decompress(compressed)
    assert decompressed == original


# ==================== 2. Encryption Tests (AES-256-GCM) ====================
def test_aes_256_gcm_encryption_integrity():
    org_id = str(uuid.uuid4())
    secret_data = b"Highly confidential database dump contents"
    associated_data = b"C:/data/confidential.db"

    # Encrypt
    res = encryption_service.encrypt(secret_data, organization_id=org_id, associated_data=associated_data)

    assert res.ciphertext != secret_data
    assert len(res.nonce_hex) == 24  # 12 bytes = 24 hex characters
    assert len(res.auth_tag_hex) == 32  # 16 bytes = 32 hex characters
    assert len(res.sha256_hash) == 64  # SHA-256 digest

    # Decrypt
    decrypted = encryption_service.decrypt(
        res.ciphertext,
        nonce_hex=res.nonce_hex,
        organization_id=org_id,
        associated_data=associated_data,
    )
    assert decrypted == secret_data

    # Isolation Test: Decryption with another org key must fail
    another_org = str(uuid.uuid4())
    with pytest.raises(Exception):
        encryption_service.decrypt(
            res.ciphertext,
            nonce_hex=res.nonce_hex,
            organization_id=another_org,
            associated_data=associated_data,
        )


# ==================== 3. MinIO Storage Tests ====================
def test_minio_storage_upload_download():
    test_path = f"test_org/test_dev/folder/sample_file/v1.enc"
    test_payload = b"\x00\x01\x02\x03\x04EncryptedPayloadData"

    saved_uri = minio_storage.upload_bytes(test_path, test_payload)
    assert "vaultguard-storage" in saved_uri

    retrieved = minio_storage.download_bytes(test_path)
    assert retrieved == test_payload


# ==================== 4. API Endpoints Integration Tests ====================
@pytest.mark.asyncio
async def test_module2_backup_pipeline_api(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(
        BackupService,
        "_run_malware_scan",
        AsyncMock(return_value=ScanResult(status=ScanStatus.CLEAN)),
    )
    # 1. Login as Super Admin
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@vaultguard.internal", "password": "AdminSecurePassword123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Org & Device for backup tests
    org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "Module2 Test Org", "contact_email": "m2@test.internal"},
        headers=headers,
    )
    org_id = org_res.json()["data"]["id"]

    dev_res = await client.post(
        "/api/v1/devices",
        json={"device_id": "M2-BACKUP-NODE", "name": "M2 Node", "os": "Ubuntu 24.04", "organization_id": org_id},
        headers=headers,
    )
    device_id = dev_res.json()["data"]["id"]

    # 3. Add Protected Folder
    folder_res = await client.post(
        "/api/v1/protected-folders",
        json={"device_id": device_id, "folder_path": "/var/data/finance", "scan_interval_seconds": 120},
        headers=headers,
    )
    assert folder_res.status_code == 201
    folder_id = folder_res.json()["data"]["id"]

    # List Protected Folders
    list_folders = await client.get("/api/v1/protected-folders", headers=headers)
    assert list_folders.status_code == 200
    assert len(list_folders.json()["data"]) >= 1

    # 4. Trigger Manual File Backup (Compress -> Encrypt -> SHA-256 -> MinIO)
    sample_content = b"Q3 Quarterly Revenue Report - Top Secret Financial Ledger Data"
    b64_content = base64.b64encode(sample_content).decode("utf-8")

    manual_res = await client.post(
        "/api/v1/backups/manual",
        json={
            "device_id": device_id,
            "file_path": "/var/data/finance/q3_ledger.xlsx",
            "file_content_base64": b64_content,
            "protected_folder_id": folder_id,
        },
        headers=headers,
    )
    assert manual_res.status_code == 201
    version_data = manual_res.json()["data"]
    assert version_data["version_number"] == 1
    assert version_data["encryption_algorithm"] == "AES-256-GCM"
    assert "file_hash_sha256" in version_data
    file_id = version_data["file_id"]

    # 5. List Snapshots
    snapshots_res = await client.get("/api/v1/backups", headers=headers)
    assert snapshots_res.status_code == 200
    assert snapshots_res.json()["data"]["total"] >= 1

    # 6. List Backup Jobs
    jobs_res = await client.get("/api/v1/backups/jobs", headers=headers)
    assert jobs_res.status_code == 200
    assert jobs_res.json()["data"]["total"] >= 1

    # 7. Check Version History for the file
    history_res = await client.get(f"/api/v1/backups/history/{file_id}", headers=headers)
    assert history_res.status_code == 200
    assert len(history_res.json()["data"]["versions"]) >= 1

    # 8. Storage Statistics
    stats_res = await client.get("/api/v1/storage/statistics", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()["data"]
    assert stats["total_files"] >= 1
    assert stats["total_versions"] >= 1
    assert stats["active_protected_folders"] >= 1

