import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models.device import Device, DeviceStatus
from app.models.future_placeholders import File, FileVersion
from app.models.organization import Organization
from app.models.protected_folder import ProtectedFolder
from app.models.ransomware import QuarantineFile
from app.models.recovery import (
    ApprovalRequest,
    RecoveryItemStatus,
    RecoveryJob,
    RecoveryJobItem,
    RecoveryJobStatus,
    RecoveryJobType,
)
from app.models.role import Role, RoleType
from app.models.user import User
from app.security.tokens import create_access_token
from app.services.recovery.path_validator import path_validator
from app.services.recovery.recovery_service import recovery_service
from app.services.scanning.malware_scanner import ScanResult, ScanStatus
from app.services.backup_service import BackupService

pytestmark = pytest.mark.asyncio


async def _seed_access_scenario():
    from tests.conftest import TestAsyncSessionLocal

    async with TestAsyncSessionLocal() as db:
        roles = {
            role.name: role
            for role in (
                await db.execute(select(Role))
            ).scalars().all()
        }
        admin = (
            await db.execute(
                select(User).where(User.email == "admin@vaultguard.internal")
            )
        ).scalar_one()
        organization = Organization(
            name="File Access Test Organization",
            slug=f"file-access-{uuid.uuid4().hex[:8]}",
            contact_email="file-access@example.test",
        )
        foreign_organization = Organization(
            name="Foreign File Access Test Organization",
            slug=f"foreign-file-access-{uuid.uuid4().hex[:8]}",
            contact_email="foreign-file-access@example.test",
        )
        db.add_all([organization, foreign_organization])
        await db.flush()
        admin.organization_id = organization.id

        employee_a = User(
            email="employee-a@example.test",
            hashed_password="not-used",
            full_name="Employee A",
            role_id=roles[RoleType.EMPLOYEE.value].id,
            organization_id=organization.id,
            is_active=True,
        )
        employee_b = User(
            email="employee-b@example.test",
            hashed_password="not-used",
            full_name="Employee B",
            role_id=roles[RoleType.EMPLOYEE.value].id,
            organization_id=organization.id,
            is_active=True,
        )
        other_admin = User(
            email="other-admin@example.test",
            hashed_password="not-used",
            full_name="Other Admin",
            role_id=roles[RoleType.ADMIN.value].id,
            organization_id=organization.id,
            is_active=True,
        )
        foreign_employee = User(
            email="foreign-employee@example.test",
            hashed_password="not-used",
            full_name="Foreign Employee",
            role_id=roles[RoleType.EMPLOYEE.value].id,
            organization_id=foreign_organization.id,
            is_active=True,
        )
        db.add_all([employee_a, employee_b, other_admin, foreign_employee])
        await db.flush()

        admin_device = Device(
            device_id=f"ADMIN-{uuid.uuid4().hex[:8]}",
            name="Admin Workstation",
            os="Windows",
            status=DeviceStatus.ONLINE,
            organization_id=organization.id,
            user_id=admin.id,
        )
        employee_a_device = Device(
            device_id=f"EMP-A-{uuid.uuid4().hex[:8]}",
            name="Employee A Workstation",
            os="Windows",
            status=DeviceStatus.ONLINE,
            organization_id=organization.id,
            user_id=employee_a.id,
        )
        employee_b_device = Device(
            device_id=f"EMP-B-{uuid.uuid4().hex[:8]}",
            name="Employee B Workstation",
            os="Windows",
            status=DeviceStatus.ONLINE,
            organization_id=organization.id,
            user_id=employee_b.id,
        )
        other_admin_device = Device(
            device_id=f"OTHER-ADMIN-{uuid.uuid4().hex[:8]}",
            name="Other Admin Workstation",
            os="Windows",
            status=DeviceStatus.ONLINE,
            organization_id=organization.id,
            user_id=other_admin.id,
        )
        foreign_employee_device = Device(
            device_id=f"FOREIGN-EMP-{uuid.uuid4().hex[:8]}",
            name="Foreign Employee Workstation",
            os="Windows",
            status=DeviceStatus.ONLINE,
            organization_id=foreign_organization.id,
            user_id=foreign_employee.id,
        )
        db.add_all([
            admin_device,
            employee_a_device,
            employee_b_device,
            other_admin_device,
            foreign_employee_device,
        ])
        await db.flush()

        files = {}
        versions = {}
        for owner_key, device in (
            ("admin", admin_device),
            ("employee_a", employee_a_device),
            ("employee_b", employee_b_device),
            ("other_admin", other_admin_device),
            ("foreign_employee", foreign_employee_device),
        ):
            file_record = File(
                organization_id=organization.id,
                device_id=device.id,
                file_path=f"C:\\VaultGuard\\{owner_key}.txt",
                original_filename=f"{owner_key}.txt",
                file_size=16,
                total_versions=1,
            )
            db.add(file_record)
            await db.flush()
            version = FileVersion(
                file_id=file_record.id,
                version_number=1,
                storage_path=f"test/{owner_key}/v1.enc",
                file_hash_sha256=hashlib.sha256(owner_key.encode()).hexdigest(),
                size_bytes=16,
                original_size_bytes=16,
                compressed_size_bytes=8,
                nonce_hex="0" * 24,
                auth_tag_hex="0" * 32,
                is_encrypted=True,
            )
            db.add(version)
            files[owner_key] = file_record
            versions[owner_key] = version

        employee_folder = ProtectedFolder(
            organization_id=organization.id,
            device_id=employee_a_device.id,
            folder_path="C:\\VaultGuard",
        )
        employee_quarantine = QuarantineFile(
            organization_id=organization.id,
            device_id=employee_a_device.id,
            user_id=employee_a.id,
            file_path="C:\\VaultGuard\\employee-threat.exe",
            file_name="employee-threat.exe",
            sha256_hash=hashlib.sha256(b"quarantined").hexdigest(),
            file_size_bytes=12,
            quarantine_path="quarantine/employee-threat.exe",
            reason="Test quarantine",
            status="QUARANTINED",
            owner_name=employee_a.full_name,
            quarantined_at=datetime.now(timezone.utc),
        )
        db.add_all([employee_folder, employee_quarantine])
        await db.flush()

        async def add_recovery_job(owner, file_record, version, status, item_status):
            job = RecoveryJob(
                organization_id=organization.id,
                requested_by_id=owner.id,
                job_type=RecoveryJobType.SINGLE_FILE.value,
                status=status,
                destination_path="recovered_files",
                total_files=1,
            )
            db.add(job)
            await db.flush()
            item = RecoveryJobItem(
                recovery_job_id=job.id,
                file_id=file_record.id,
                file_version_id=version.id,
                original_path=file_record.file_path,
                target_path=file_record.file_path,
                status=item_status,
                sha256_verified=item_status == RecoveryItemStatus.COMPLETED.value,
            )
            db.add(item)
            return job

        employee_job = await add_recovery_job(
            employee_a,
            files["employee_a"],
            versions["employee_a"],
            RecoveryJobStatus.PENDING.value,
            RecoveryItemStatus.PENDING.value,
        )
        employee_b_job = await add_recovery_job(
            employee_b,
            files["employee_b"],
            versions["employee_b"],
            RecoveryJobStatus.FAILED.value,
            RecoveryItemStatus.FAILED.value,
        )
        employee_approval = ApprovalRequest(
            organization_id=organization.id,
            requested_by_id=employee_a.id,
            request_type="RECOVERY_SINGLE_FILE",
            status="PENDING",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(employee_approval)
        await db.flush()
        employee_job.approval_request_id = employee_approval.id
        await db.commit()

        def token(user, role):
            return create_access_token(
                subject=str(user.id),
                role=role,
                organization_id=str(organization.id),
            )

        return {
            "admin_token": token(admin, RoleType.ADMIN.value),
            "employee_a_token": token(employee_a, RoleType.EMPLOYEE.value),
            "employee_b_token": token(employee_b, RoleType.EMPLOYEE.value),
            "admin_device_id": str(admin_device.id),
            "employee_a_device_id": str(employee_a_device.id),
            "employee_a_device_tag": employee_a_device.device_id,
            "employee_b_device_id": str(employee_b_device.id),
            "employee_a_id": str(employee_a.id),
            "employee_b_id": str(employee_b.id),
            "foreign_employee_id": str(foreign_employee.id),
            "foreign_organization_id": str(foreign_organization.id),
            "other_admin_device_id": str(other_admin_device.id),
            "other_admin_device_tag": other_admin_device.device_id,
            "employee_a_file_id": str(files["employee_a"].id),
            "employee_b_file_id": str(files["employee_b"].id),
            "employee_a_version_id": str(versions["employee_a"].id),
            "employee_b_version_id": str(versions["employee_b"].id),
            "employee_job_id": str(employee_job.id),
            "employee_approval_id": str(employee_approval.id),
            "employee_b_job_id": str(employee_b_job.id),
            "employee_folder_id": str(employee_folder.id),
            "employee_quarantine_id": str(employee_quarantine.id),
        }


@pytest.fixture
async def access_scenario(client):
    return await _seed_access_scenario()


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


async def test_admin_can_upload_and_restore_own_file(client, access_scenario, monkeypatch, tmp_path):
    from app.services import backup_service

    clean_result = ScanResult(
        status=ScanStatus.CLEAN,
        sha256=hashlib.sha256(b"clean admin file").hexdigest(),
        file_size=len(b"clean admin file"),
    )
    monkeypatch.setattr(BackupService, "_run_malware_scan", AsyncMock(return_value=clean_result))
    monkeypatch.setattr(
        backup_service.minio_storage,
        "upload_bytes",
        lambda object_path, data, content_type=None: f"vaultguard-storage/{object_path}",
    )
    monkeypatch.setattr(backup_service, "publish_backup_completed_event", AsyncMock())

    upload = await client.post(
        "/api/v1/backups/manual",
        data={
            "device_id": access_scenario["admin_device_id"],
            "file_path": "C:\\VaultGuard\\admin-upload.txt",
        },
        files={"file": ("admin-upload.txt", b"clean admin file", "text/plain")},
        headers=_headers(access_scenario["admin_token"]),
    )
    assert upload.status_code == 201, upload.text
    version_id = upload.json()["data"]["id"]

    backup_job = await client.post(
        "/api/v1/backups/start",
        json={
            "device_id": access_scenario["admin_device_id"],
            "job_type": "FULL",
        },
        headers=_headers(access_scenario["admin_token"]),
    )
    assert backup_job.status_code == 201, backup_job.text

    monkeypatch.setattr(path_validator, "safe_root", str(tmp_path / "restored"))
    monkeypatch.setattr(path_validator, "STAGING_ROOT", str(tmp_path / "staging"))

    async def verified_payload(db, job, item):
        return b"clean admin file"

    monkeypatch.setattr(recovery_service, "get_verified_item_payload", verified_payload)
    restore = await client.post(
        "/api/v1/recovery/restore/single",
        json={"file_version_id": version_id},
        headers=_headers(access_scenario["admin_token"]),
    )
    assert restore.status_code == 201, restore.text
    assert restore.json()["data"]["status"] == RecoveryJobStatus.COMPLETED.value
    assert (tmp_path / "restored" / "admin-upload.txt").read_bytes() == b"clean admin file"


async def test_admin_employee_views_are_read_only(client, access_scenario):
    admin_headers = _headers(access_scenario["admin_token"])

    employee_backups = await client.get(
        "/api/v1/backups?owner_scope=employees", headers=admin_headers
    )
    assert employee_backups.status_code == 200
    employee_file_ids = {item["file_id"] for item in employee_backups.json()["data"]["items"]}
    assert access_scenario["employee_a_file_id"] in employee_file_ids
    assert access_scenario["employee_b_file_id"] in employee_file_ids
    assert len(employee_file_ids) == 2

    own_backups = await client.get("/api/v1/backups?owner_scope=mine", headers=admin_headers)
    assert own_backups.status_code == 200
    assert {
        item["file_id"] for item in own_backups.json()["data"]["items"]
    }.isdisjoint(employee_file_ids)
    assert own_backups.json()["data"]["total"] == 1

    visible_devices = await client.get("/api/v1/devices", headers=admin_headers)
    assert visible_devices.status_code == 200
    assert visible_devices.json()["data"]["total"] == 3
    blocked_other_admin_device = await client.get(
        f"/api/v1/devices/{access_scenario['other_admin_device_tag']}",
        headers=admin_headers,
    )
    assert blocked_other_admin_device.status_code == 403

    storage_stats = await client.get("/api/v1/storage/statistics", headers=admin_headers)
    assert storage_stats.status_code == 200
    assert storage_stats.json()["data"]["total_files"] == 3

    history = await client.get(
        f"/api/v1/backups/history/{access_scenario['employee_a_file_id']}",
        headers=admin_headers,
    )
    assert history.status_code == 200

    employee_job = await client.get(
        f"/api/v1/recovery/jobs/{access_scenario['employee_job_id']}",
        headers=admin_headers,
    )
    assert employee_job.status_code == 200
    assert (
        await client.post(
            f"/api/v1/recovery/jobs/{access_scenario['employee_job_id']}/cancel",
            headers=admin_headers,
        )
    ).status_code == 400
    blocked_approval = await client.post(
        f"/api/v1/recovery/approvals/{access_scenario['employee_approval_id']}/action",
        json={"action": "APPROVE"},
        headers=admin_headers,
    )
    assert blocked_approval.status_code == 403
    assert (
        await client.post(
            f"/api/v1/recovery/jobs/{access_scenario['employee_b_job_id']}/retry",
            headers=admin_headers,
        )
    ).status_code == 400

    blocked_upload = await client.post(
        "/api/v1/backups/manual",
        data={
            "device_id": access_scenario["employee_a_device_id"],
            "file_path": "C:\\VaultGuard\\admin-overwrite.txt",
        },
        files={"file": ("admin-overwrite.txt", b"no", "text/plain")},
        headers=admin_headers,
    )
    assert blocked_upload.status_code == 403


    blocked_job = await client.post(
        "/api/v1/backups/start",
        json={
            "device_id": access_scenario["employee_a_device_id"],
            "job_type": "FULL",
        },
        headers=admin_headers,
    )
    assert blocked_job.status_code == 403

    blocked_restore = await client.post(
        "/api/v1/recovery/restore/single",
        json={"file_version_id": access_scenario["employee_a_version_id"]},
        headers=admin_headers,
    )
    assert blocked_restore.status_code == 400

    blocked_device_update = await client.put(
        f"/api/v1/devices/{access_scenario['employee_a_device_tag']}",
        json={"name": "Admin changed employee device"},
        headers=admin_headers,
    )
    assert blocked_device_update.status_code == 403

    blocked_owner_change = await client.put(
        f"/api/v1/devices/{access_scenario['employee_a_device_tag']}",
        json={"user_id": "00000000-0000-0000-0000-000000000001"},
        headers=admin_headers,
    )
    assert blocked_owner_change.status_code == 422

    blocked_folder_delete = await client.delete(
        f"/api/v1/protected-folders/{access_scenario['employee_folder_id']}",
        headers=admin_headers,
    )
    assert blocked_folder_delete.status_code == 403

    employee_quarantines = await client.get(
        "/api/v1/ransomware/quarantine", headers=admin_headers
    )
    assert employee_quarantines.status_code == 200
    assert any(
        item["id"] == access_scenario["employee_quarantine_id"]
        for item in employee_quarantines.json()["data"]
    )
    blocked_quarantine_restore = await client.post(
        "/api/v1/ransomware/restore",
        json={"quarantine_id": access_scenario["employee_quarantine_id"]},
        headers=admin_headers,
    )
    assert blocked_quarantine_restore.status_code == 404
    blocked_quarantine_delete = await client.delete(
        f"/api/v1/ransomware/quarantine/{access_scenario['employee_quarantine_id']}",
        headers=admin_headers,
    )
    assert blocked_quarantine_delete.status_code == 404

    blocked_quarantine_create = await client.post(
        "/api/v1/ransomware/quarantine",
        json={
            "device_id": access_scenario["employee_a_device_id"],
            "file_path": "C:\\VaultGuard\\employee.txt",
            "reason": "Unauthorized Admin action",
        },
        headers=admin_headers,
    )
    assert blocked_quarantine_create.status_code == 403

    blocked_simulation = await client.post(
        "/api/v1/ransomware/simulate",
        json={"device_id": access_scenario["employee_a_device_id"]},
        headers=admin_headers,
    )
    assert blocked_simulation.status_code == 403

    assert (
        await client.put(
            f"/api/v1/backups/history/{access_scenario['employee_a_file_id']}",
            json={"file_path": "overwritten.txt"},
            headers=admin_headers,
        )
    ).status_code == 405
    assert (
        await client.delete(
            f"/api/v1/backups/history/{access_scenario['employee_a_file_id']}",
            headers=admin_headers,
        )
    ).status_code == 405


async def test_employee_backup_dashboard_is_organization_and_owner_scoped(
    client, access_scenario
):
    admin_headers = _headers(access_scenario["admin_token"])
    employees = await client.get("/api/v1/backups/employees", headers=admin_headers)
    assert employees.status_code == 200, employees.text
    summaries = employees.json()["data"]
    assert {item["employee_id"] for item in summaries} == {
        access_scenario["employee_a_id"],
        access_scenario["employee_b_id"],
    }
    summary_a = next(
        item for item in summaries
        if item["employee_id"] == access_scenario["employee_a_id"]
    )
    assert summary_a["total_backup_files"] == 1
    assert summary_a["storage_used_bytes"] == 16
    assert summary_a["last_backup_at"] is not None

    details_a = await client.get(
        f"/api/v1/backups/employees/{access_scenario['employee_a_id']}",
        headers=admin_headers,
    )
    details_b = await client.get(
        f"/api/v1/backups/employees/{access_scenario['employee_b_id']}",
        headers=admin_headers,
    )
    assert details_a.status_code == 200, details_a.text
    assert details_b.status_code == 200, details_b.text
    files_a = details_a.json()["data"]["files"]["items"]
    files_b = details_b.json()["data"]["files"]["items"]
    assert {item["id"] for item in files_a} == {
        access_scenario["employee_a_file_id"]
    }
    assert {item["id"] for item in files_b} == {
        access_scenario["employee_b_file_id"]
    }
    assert "storage_path" not in files_a[0]["versions"][0]
    recovery_ids_a = {
        item["id"]
        for item in details_a.json()["data"]["recovery_history"]["items"]
    }
    recovery_ids_b = {
        item["id"]
        for item in details_b.json()["data"]["recovery_history"]["items"]
    }
    assert recovery_ids_a == {access_scenario["employee_job_id"]}
    assert recovery_ids_b == {access_scenario["employee_b_job_id"]}

    foreign_employee = await client.get(
        f"/api/v1/backups/employees/{access_scenario['foreign_employee_id']}",
        headers=admin_headers,
    )
    assert foreign_employee.status_code == 404
    denied_employee_list = await client.get(
        "/api/v1/backups/employees",
        headers=_headers(access_scenario["employee_a_token"]),
    )
    assert denied_employee_list.status_code == 403


async def test_employee_cannot_access_another_employees_file_or_job(
    client, access_scenario, monkeypatch, tmp_path
):
    from app.services import backup_service

    employee_headers = _headers(access_scenario["employee_a_token"])

    other_device_backups = await client.get(
        f"/api/v1/backups?device_id={access_scenario['employee_b_device_id']}",
        headers=employee_headers,
    )
    assert other_device_backups.status_code == 200
    assert other_device_backups.json()["data"]["total"] == 0

    other_history = await client.get(
        f"/api/v1/backups/history/{access_scenario['employee_b_file_id']}",
        headers=employee_headers,
    )
    assert other_history.status_code == 404

    other_job = await client.get(
        f"/api/v1/recovery/jobs/{access_scenario['employee_b_job_id']}",
        headers=employee_headers,
    )
    assert other_job.status_code == 404

    blocked_restore = await client.post(
        "/api/v1/recovery/restore/single",
        json={"file_version_id": access_scenario["employee_b_version_id"]},
        headers=employee_headers,
    )
    assert blocked_restore.status_code == 400

    blocked_cancel = await client.post(
        f"/api/v1/recovery/jobs/{access_scenario['employee_b_job_id']}/cancel",
        headers=employee_headers,
    )
    assert blocked_cancel.status_code == 400

    blocked_retry = await client.post(
        f"/api/v1/recovery/jobs/{access_scenario['employee_b_job_id']}/retry",
        headers=employee_headers,
    )
    assert blocked_retry.status_code == 400

    blocked_quarantine_restore = await client.post(
        "/api/v1/ransomware/restore",
        json={"quarantine_id": access_scenario["employee_quarantine_id"]},
        headers=_headers(access_scenario["employee_b_token"]),
    )
    assert blocked_quarantine_restore.status_code == 404
    blocked_quarantine_delete = await client.delete(
        f"/api/v1/ransomware/quarantine/{access_scenario['employee_quarantine_id']}",
        headers=_headers(access_scenario["employee_b_token"]),
    )
    assert blocked_quarantine_delete.status_code == 404

    monkeypatch.setattr(
        BackupService,
        "_run_malware_scan",
        AsyncMock(return_value=ScanResult(status=ScanStatus.CLEAN)),
    )
    monkeypatch.setattr(
        backup_service.minio_storage,
        "upload_bytes",
        lambda object_path, data, content_type=None: f"vaultguard-storage/{object_path}",
    )
    monkeypatch.setattr(backup_service, "publish_backup_completed_event", AsyncMock())
    own_upload = await client.post(
        "/api/v1/backups/manual",
        data={
            "device_id": access_scenario["employee_a_device_id"],
            "file_path": "C:\\VaultGuard\\employee-own-upload.txt",
        },
        files={"file": ("employee-own-upload.txt", b"employee data", "text/plain")},
        headers=employee_headers,
    )
    assert own_upload.status_code == 201, own_upload.text

    own_backup_job = await client.post(
        "/api/v1/backups/start",
        json={
            "device_id": access_scenario["employee_a_device_id"],
            "job_type": "FULL",
        },
        headers=employee_headers,
    )
    assert own_backup_job.status_code == 201, own_backup_job.text

    monkeypatch.setattr(path_validator, "safe_root", str(tmp_path / "employee-restored"))
    monkeypatch.setattr(path_validator, "STAGING_ROOT", str(tmp_path / "employee-staging"))

    async def verified_payload(db, job, item):
        return b"employee a file"

    monkeypatch.setattr(recovery_service, "get_verified_item_payload", verified_payload)
    own_restore = await client.post(
        "/api/v1/recovery/restore/single",
        json={"file_version_id": access_scenario["employee_a_version_id"]},
        headers=employee_headers,
    )
    assert own_restore.status_code == 201, own_restore.text
    assert own_restore.json()["data"]["status"] == RecoveryJobStatus.COMPLETED.value
    assert (tmp_path / "employee-restored" / "employee_a.txt").read_bytes() == b"employee a file"
