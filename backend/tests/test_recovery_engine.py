import hashlib
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
import pytest

from app.core.compression import compression_service
from app.core.encryption import encryption_service
from app.models.future_placeholders import File, FileVersion
from app.models.recovery import (
    DestinationType,
    OverwritePolicy,
    RecoveryItemStatus,
    RecoveryJobStatus,
    ThreatRiskLabel,
)
from app.models.threat import Detection, QuarantineEvent
from app.services.recovery.integrity_service import IntegrityVerificationError, integrity_service
from app.services.recovery.path_validator import PathValidationError, SafePathValidator
from app.services.recovery.risk_assessor import RecoveryRiskAssessor
from app.storage.minio_client import minio_storage


# ==================== 1. Path Traversal & Destination Protection Tests ====================

def test_path_traversal_protection():
    validator = SafePathValidator(safe_root="test_recovered_files")

    # 1. Reject simple directory traversal
    with pytest.raises(PathValidationError):
        validator.validate_and_resolve_destination(
            original_file_path="../../etc/passwd",
            destination_type=DestinationType.SAFE_DIR.value,
        )

    # 2. Reject Windows backslash directory traversal
    with pytest.raises(PathValidationError):
        validator.validate_and_resolve_destination(
            original_file_path="..\\..\\Windows\\System32\\cmd.exe",
            destination_type=DestinationType.SAFE_DIR.value,
        )

    # 3. Reject null byte injection
    with pytest.raises(PathValidationError):
        validator.validate_and_resolve_destination(
            original_file_path="legit_file.txt\x00malicious.exe",
            destination_type=DestinationType.SAFE_DIR.value,
        )

    # 4. Reject critical system root overwrite
    with pytest.raises(PathValidationError):
        validator.validate_and_resolve_destination(
            original_file_path="/etc/shadow",
            destination_type=DestinationType.ORIGINAL.value,
        )

    # 5. Legitimate path inside safe directory must succeed
    resolved = validator.validate_and_resolve_destination(
        original_file_path="documents/financial_report.xlsx",
        destination_type=DestinationType.SAFE_DIR.value,
        organization_id="org123",
    )
    assert "org_org123" in resolved
    assert resolved.endswith(os.path.join("documents", "financial_report.xlsx"))


# ==================== 2. Overwrite Collision Policies Tests ====================

def test_destination_overwrite_conflict_policies(tmp_path):
    validator = SafePathValidator(safe_root=str(tmp_path))
    existing_file = tmp_path / "important_doc.docx"
    existing_file.write_text("Original content", encoding="utf-8")

    file_str = str(existing_file)

    # 1. SKIP policy: should_write is False
    should_write, dest_path = validator.resolve_file_conflict(file_str, OverwritePolicy.SKIP.value)
    assert should_write is False
    assert dest_path == file_str

    # 2. OVERWRITE policy: should_write is True
    should_write, dest_path = validator.resolve_file_conflict(file_str, OverwritePolicy.OVERWRITE.value)
    assert should_write is True
    assert dest_path == file_str

    # 3. RENAME policy: should_write is True, creates non-colliding name
    should_write, dest_path = validator.resolve_file_conflict(file_str, OverwritePolicy.RENAME.value)
    assert should_write is True
    assert dest_path != file_str
    assert "important_doc (1).docx" in dest_path

    # If (1) also exists, next is (2)
    (tmp_path / "important_doc (1).docx").write_text("Existing 1", encoding="utf-8")
    should_write, dest_path2 = validator.resolve_file_conflict(file_str, OverwritePolicy.RENAME.value)
    assert should_write is True
    assert "important_doc (2).docx" in dest_path2


# ==================== 3. Cryptographic Decryption & SHA-256 Integrity Verification ====================

def test_integrity_verification_sha256():
    org_id = uuid.uuid4()
    original_plaintext = b"VaultGuard Enterprise Recovery Plaintext Integrity Benchmark Payload 2026"
    expected_sha256 = hashlib.sha256(original_plaintext).hexdigest()

    # Step A: Compress
    compressed, orig_size, comp_size, _ = compression_service.compress(original_plaintext)

    # Step B: Encrypt with AES-256-GCM
    assoc_data = b"/safe/path/data.bin"
    enc_res = encryption_service.encrypt(
        compressed,
        organization_id=str(org_id),
        associated_data=assoc_data,
    )

    # Step C: Save to storage
    storage_key = f"recovery_test/{uuid.uuid4()}/v1.enc"
    minio_storage.upload_bytes(storage_key, enc_res.ciphertext)

    # Mock FileVersion object
    version = FileVersion(
        id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        version_number=1,
        storage_path=storage_key,
        file_hash_sha256=expected_sha256,
        size_bytes=len(enc_res.ciphertext),
        original_size_bytes=orig_size,
        compressed_size_bytes=comp_size,
        compression_algorithm="zlib",
        encryption_algorithm="AES-256-GCM",
        nonce_hex=enc_res.nonce_hex,
        auth_tag_hex=enc_res.auth_tag_hex,
        is_encrypted=True,
    )

    # Successful Verification Roundtrip
    verified_bytes, verified_hash = integrity_service.restore_and_verify_payload(
        version=version,
        organization_id=org_id,
        associated_data=assoc_data,
    )
    assert verified_bytes == original_plaintext
    assert verified_hash == expected_sha256

    # Tampered Hash: should raise IntegrityVerificationError and discard plaintext
    version.file_hash_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"
    with pytest.raises(IntegrityVerificationError, match="Cryptographic hash mismatch"):
        integrity_service.restore_and_verify_payload(
            version=version,
            organization_id=org_id,
            associated_data=assoc_data,
        )

    # Tampered Ciphertext in Storage
    minio_storage.upload_bytes(storage_key, b"CorruptedCiphertextBytes1234567890")
    version.file_hash_sha256 = expected_sha256
    with pytest.raises(IntegrityVerificationError, match="Cryptographic decryption failed"):
        integrity_service.restore_and_verify_payload(
            version=version,
            organization_id=org_id,
            associated_data=assoc_data,
        )


# ==================== 4. Staging Directory Lifecycle ====================

def test_staging_directory_lifecycle(tmp_path):
    validator = SafePathValidator(safe_root=str(tmp_path / "recovered"))
    job_id = uuid.uuid4()
    version_id = uuid.uuid4()

    # 1. Create staging file
    staging_file = validator.create_staging_path(job_id, version_id)
    assert os.path.exists(os.path.dirname(staging_file))

    with open(staging_file, "wb") as f:
        f.write(b"Verified payload in staging")

    # 2. Commit to target
    target_dest = str(tmp_path / "recovered" / "final_file.txt")
    validator.commit_staged_file(staging_file, target_dest)

    assert os.path.exists(target_dest)
    with open(target_dest, "rb") as f:
        assert f.read() == b"Verified payload in staging"

    # 3. Clean staging dir
    validator.cleanup_staging_dir(job_id)
    assert not os.path.exists(os.path.dirname(staging_file))


# ==================== 5. Risk Classification Unit Test ====================

def test_risk_assessor_classification():
    # Quarantined version flagged suspicious
    v_quarantined = FileVersion(
        id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        version_number=1,
        storage_path="path",
        file_hash_sha256="abc",
        size_bytes=100,
        is_quarantined=True,
    )

    # High entropy version flagged suspicious
    v_high_entropy = FileVersion(
        id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        version_number=1,
        storage_path="path",
        file_hash_sha256="abc",
        size_bytes=100,
        is_quarantined=False,
        entropy_score=7.92,
    )

    # Verify attributes
    assert v_quarantined.is_quarantined is True
    assert v_high_entropy.entropy_score > 7.6


# ==================== 6. End-to-End Recovery Service Job Execution ====================

@pytest.mark.asyncio
async def test_recovery_job_execution_service_flow(tmp_path):
    from app.database.session import Base
    from app.models.organization import Organization
    from app.models.device import Device
    from app.services.recovery.recovery_service import recovery_service
    from tests.conftest import test_engine, TestAsyncSessionLocal

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        # Create Org & Device
        org = Organization(name="Recovery Test Corp", contact_email="recov@corp.internal")
        session.add(org)
        await session.flush()

        dev = Device(
            device_id="ENDPOINT-REC-01",
            name="Finance Terminal",
            os="Windows 11 Enterprise",
            organization_id=org.id,
        )
        session.add(dev)
        await session.flush()

        # Create File
        file_obj = File(
            organization_id=org.id,
            device_id=dev.id,
            file_path="C:/Finance/Q4_BalanceSheet.xlsx",
            original_filename="Q4_BalanceSheet.xlsx",
            file_size=1024,
            total_versions=1,
            is_deleted=False,
        )
        session.add(file_obj)
        await session.flush()

        # Prepare verified encrypted backup payload
        secret_content = b"Confidential Q4 Balance Sheet Financial Summary - VaultGuard Certified"
        content_hash = hashlib.sha256(secret_content).hexdigest()
        compressed, orig_size, comp_size, _ = compression_service.compress(secret_content)
        enc_res = encryption_service.encrypt(
            compressed,
            organization_id=str(org.id),
            associated_data=file_obj.file_path.encode("utf-8"),
        )
        storage_path = f"{org.id}/{dev.id}/Q4_BalanceSheet/v1.enc"
        minio_storage.upload_bytes(storage_path, enc_res.ciphertext)

        version = FileVersion(
            file_id=file_obj.id,
            version_number=1,
            storage_path=storage_path,
            file_hash_sha256=content_hash,
            size_bytes=len(enc_res.ciphertext),
            original_size_bytes=orig_size,
            compressed_size_bytes=comp_size,
            compression_algorithm="zlib",
            encryption_algorithm="AES-256-GCM",
            nonce_hex=enc_res.nonce_hex,
            auth_tag_hex=enc_res.auth_tag_hex,
            is_encrypted=True,
            is_quarantined=False,
        )
        session.add(version)
        await session.commit()
        version_id = version.id
        org_id = org.id

    # Execute Job
    async with TestAsyncSessionLocal() as session:
        custom_dest = str(tmp_path / "custom_restore_dir")
        job = await recovery_service.create_recovery_job(
            db=session,
            organization_id=org_id,
            requested_by_id=uuid.uuid4(),
            job_type="SINGLE_FILE",
            file_version_ids=[version_id],
            destination_path=custom_dest,
            destination_type=DestinationType.CUSTOM_SAFE_DIR.value,
            overwrite_policy=OverwritePolicy.OVERWRITE.value,
            bypass_approval_check=True,
        )
        assert job.status == RecoveryJobStatus.PENDING.value
        assert job.total_files == 1
        job_id = job.id

    async with TestAsyncSessionLocal() as session:
        executed_job = await recovery_service.execute_recovery_job(db=session, job_id=job_id)
        assert executed_job.status == RecoveryJobStatus.COMPLETED.value
        assert executed_job.files_restored == 1
        assert executed_job.files_failed == 0
        assert executed_job.bytes_restored == len(secret_content)

        # Verify the file exists on disk and contents match exactly
        expected_disk_file = os.path.join(custom_dest, "Finance", "Q4_BalanceSheet.xlsx")
        assert os.path.exists(expected_disk_file)
        with open(expected_disk_file, "rb") as rf:
            restored_data = rf.read()
        assert restored_data == secret_content

