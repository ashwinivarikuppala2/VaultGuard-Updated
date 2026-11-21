import asyncio
import base64
import hashlib
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.compression import compression_service
from app.core.encryption import encryption_service
from app.core.events import publish_backup_completed_event
from app.core.exceptions import (
    AuthorizationException,
    EntityNotFoundException,
    MalwareDetectedException,
    VaultGuardException,
)
from app.services.scanning.malware_scanner import malware_scanner, ScanStatus
from app.services.alerts.alert_service import alert_service

logger = logging.getLogger("vaultguard.backup")
from app.models.device import Device
from app.models.future_placeholders import BackupJob, File, FileScanEvent, FileVersion
from app.models.recovery import RecoveryJob, RecoveryJobItem
from app.models.role import Role
from app.models.protected_folder import ProtectedFolder
from app.models.role import RoleType
from app.models.user import User
from app.repositories.backup_repository import BackupRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.backup import (
    BackupJobResponse,
    BackupSnapshotResponse,
    EmployeeBackupDetails,
    EmployeeBackupFile,
    EmployeeBackupProfile,
    EmployeeBackupSummary,
    EmployeeBackupVersion,
    EmployeeRecoveryHistoryItem,
    FileHistoryItem,
    FileVersionResponse,
    ManualBackupRequest,
    StartBackupRequest,
)
from app.schemas.common import PaginatedResponse
from app.services.audit_service import AuditService
from app.storage.minio_client import minio_storage


class BackupService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = BackupRepository(db)
        self.device_repo = DeviceRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.audit_service = AuditService(db)

    def _assert_device_owner(self, device: Device, current_user: User) -> None:
        role_name = current_user.role.name
        if role_name == RoleType.ADMIN.value:
            allowed = (
                device.user_id == current_user.id
                and device.organization_id == current_user.organization_id
            )
        elif role_name in (RoleType.EMPLOYEE.value, RoleType.INDIVIDUAL.value):
            allowed = (
                device.user_id == current_user.id
                and device.organization_id == current_user.organization_id
            )
        else:
            allowed = False

        if not allowed:
            raise AuthorizationException("Backups are only permitted for devices owned by the authenticated user.")

    async def _validate_protected_folder(
        self,
        device_id: uuid.UUID,
        protected_folder_id: Optional[uuid.UUID],
    ) -> None:
        if protected_folder_id is None:
            return
        folder = await self.db.get(ProtectedFolder, protected_folder_id)
        if not folder or folder.device_id != device_id:
            raise AuthorizationException("The protected folder does not belong to the selected device.")

    async def _visible_device_ids(
        self,
        current_user: User,
        owner_scope: Optional[str] = None,
    ) -> List[uuid.UUID]:
        if current_user.role.name == RoleType.ADMIN.value:
            my_ids = await self.device_repo.list_ids_by_user(
                current_user.id, current_user.organization_id
            )
            employee_ids = (
                await self.device_repo.list_employee_ids_by_organization(current_user.organization_id)
                if current_user.organization_id
                else []
            )
            if owner_scope == "mine" or not current_user.organization_id:
                return my_ids
            if owner_scope == "employees":
                return employee_ids
            return list(dict.fromkeys([*my_ids, *employee_ids]))

        if current_user.role.name in (RoleType.EMPLOYEE.value, RoleType.INDIVIDUAL.value):
            return await self.device_repo.list_ids_by_user(
                current_user.id, current_user.organization_id
            )
        return []

    def _sanitize_path_segment(self, segment: str) -> str:
        """Sanitizes file and folder names for S3 object paths."""
        cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", segment)
        return cleaned.strip("_") or "root"

    def build_s3_object_path(
        self,
        organization_slug: str,
        device_tag: str,
        folder_name: str,
        filename: str,
        version_number: int,
    ) -> str:
        """Object path format: organization/device/folder/filename/version.enc"""
        safe_org = self._sanitize_path_segment(organization_slug)
        safe_dev = self._sanitize_path_segment(device_tag)
        safe_folder = self._sanitize_path_segment(folder_name)
        safe_file = self._sanitize_path_segment(filename)
        return f"{safe_org}/{safe_dev}/{safe_folder}/{safe_file}/v{version_number}.enc"

    async def start_backup_job(
        self,
        request_in: StartBackupRequest,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> BackupJobResponse:
        """Initiate a backup job record for a fleet device."""
        device = await self.device_repo.get_by_id(request_in.device_id)
        if not device:
            raise EntityNotFoundException("Device", request_in.device_id)

        self._assert_device_owner(device, current_user)
        await self._validate_protected_folder(
            device.id, getattr(request_in, "protected_folder_id", None)
        )

        job = await self.repository.create_job(
            organization_id=device.organization_id,
            device_id=device.id,
            job_type=request_in.job_type,
        )

        await self.audit_service.log(
            action="BACKUP_JOB_STARTED",
            resource_type="BackupJob",
            resource_id=str(job.id),
            organization_id=device.organization_id,
            user_id=current_user.id,
            details={"device_id": str(device.id), "job_type": request_in.job_type},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return BackupJobResponse.model_validate(job)

    async def _run_malware_scan(self, raw_bytes: bytes, filename: str) -> "ScanResult":
        """Run ClamAV scan in a thread pool to avoid blocking the async event loop.
        Extracted as a separate method so unit tests can patch it with AsyncMock."""
        return await asyncio.to_thread(malware_scanner.scan_bytes, raw_bytes, filename)

    async def process_file_backup(
        self,
        organization_id: Optional[uuid.UUID],
        device_id: uuid.UUID,
        file_path: str,
        raw_bytes: bytes,
        protected_folder_id: Optional[uuid.UUID] = None,
        job_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> FileVersion:
        """Core backup pipeline:
        SCAN (ClamAV) -> Compress -> Encrypt (AES-256-GCM) -> SHA-256 -> MinIO Upload -> DB Version -> Event Publish
        """
        device = await self.device_repo.get_by_id(device_id)
        if not device:
            raise EntityNotFoundException("Device", device_id)
        if device.organization_id != organization_id:
            raise AuthorizationException("Backup organization does not match the device owner.")
        await self._validate_protected_folder(device.id, protected_folder_id)
        if user_id is not None and device.user_id != user_id:
            raise AuthorizationException("Backup owner does not match the selected device.")
        if job_id is not None:
            job = await self.repository.get_job_by_id(job_id)
            if (
                not job
                or job.device_id != device.id
                or job.organization_id != organization_id
            ):
                raise AuthorizationException("Backup job does not belong to the selected device.")

        if organization_id:
            org = await self.org_repo.get_by_id(organization_id)
            if not org:
                raise EntityNotFoundException("Organization", organization_id)
            org_slug = org.slug
            tenant_key = str(organization_id)
        else:
            org_slug = f"personal-{device.user_id}"
            tenant_key = f"personal-{device.user_id}"

        filename = os.path.basename(file_path) or "file"

        # ── STEP 0: MANDATORY PRE-BACKUP MALWARE SCAN ──────────────────────
        # Scan RAW plaintext bytes BEFORE compress/encrypt. Runs in a thread
        # via _run_malware_scan() so the synchronous socket call never blocks
        # the async event loop. Tests patch _run_malware_scan with AsyncMock.
        scan_result = await self._run_malware_scan(raw_bytes, filename)

        if scan_result.should_block:
            # Persist a FileScanEvent even for files that never become FileVersions
            scan_event = FileScanEvent(
                organization_id=organization_id,
                device_id=device_id,
                user_id=user_id,
                filename=filename,
                sha256=scan_result.sha256,
                file_size=scan_result.file_size,
                scan_status=scan_result.status.value,
                detection_name=scan_result.detection_name,
                detection_category=scan_result.detection_category,
                is_ransomware_related=scan_result.is_ransomware_related,
                backup_blocked=True,
            )

            self.db.add(scan_event)
            await self.db.flush()

            # Create a persistent security alert
            if organization_id:
                severity = "CRITICAL" if scan_result.is_ransomware_related else "HIGH"
                category_str = (
                    f" [{scan_result.detection_category}]"
                    if scan_result.detection_category else ""
                )
                try:
                    alert = await alert_service.create_alert(
                        db=self.db,
                        organization_id=organization_id,
                        device_id=device_id,
                        title=(
                            "🚨 RANSOMWARE Detected: Backup Blocked"
                            if scan_result.is_ransomware_related
                            else "🚨 Malware Detected: Backup Blocked"
                        ),
                        description=(
                            f"File '{filename}' was blocked from backup. "
                            f"Scan status: {scan_result.status.value}{category_str}. "
                            f"Detection: {scan_result.detection_name or 'N/A'}. "
                            f"SHA-256: {scan_result.sha256}. "
                            "File was not written to MinIO."
                        ),
                        severity=severity,
                    )
                    scan_event.alert_id = alert.id
                except Exception as alert_err:
                    logger.error("Failed to create malware alert: %s", alert_err)

            await self.db.commit()

            await self.audit_service.log(
                action="BACKUP_BLOCKED_MALWARE",
                resource_type="FileScanEvent",
                resource_id=str(scan_event.id),
                organization_id=organization_id,
                user_id=user_id,
                details={
                    "filename": filename,
                    "scan_status": scan_result.status.value,
                    "detection_name": scan_result.detection_name,
                    "sha256": scan_result.sha256,
                    "is_ransomware_related": scan_result.is_ransomware_related,
                },
            )

            raise MalwareDetectedException(scan_result)
        # ── END MALWARE SCAN GATE ───────────────────────────────────────────

        # 1. Compress raw content
        compressed_bytes, orig_size, comp_size, ratio = compression_service.compress(raw_bytes)

        # 2. Encrypt with AES-256-GCM (isolated tenant key)
        enc_res = encryption_service.encrypt(
            plaintext=compressed_bytes,
            organization_id=tenant_key,
            associated_data=file_path.encode("utf-8"),
        )

        # Compute SHA-256 of the ORIGINAL raw bytes (pre-compression, pre-encryption).
        # CRITICAL: The recovery pipeline decrypts → decompresses → hashes plaintext
        # and compares against file_hash_sha256. Must store hash of original content.
        raw_plaintext_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # 3. Retrieve or create File record to obtain next version number
        file_record = await self.repository.get_or_create_file(
            organization_id=organization_id,
            device_id=device_id,
            file_path=file_path,
            protected_folder_id=protected_folder_id,
        )
        next_version = file_record.total_versions + 1

        # 4. Construct MinIO object path: organization/device/folder/filename/version.enc
        parent_folder = os.path.basename(os.path.dirname(file_path)) or "default"
        object_path = self.build_s3_object_path(
            organization_slug=org_slug,
            device_tag=device.device_id,
            folder_name=parent_folder,
            filename=filename,
            version_number=next_version,
        )

        # 5. Upload encrypted payload to MinIO
        storage_uri = minio_storage.upload_bytes(
            object_path=object_path,
            data=enc_res.ciphertext,
            content_type="application/octet-stream",
        )

        # 6. Save version metadata in PostgreSQL (with CLEAN scan stamp)
        version = await self.repository.create_file_version(
            file_record=file_record,
            storage_path=storage_uri,
            file_hash_sha256=raw_plaintext_sha256,
            original_size=orig_size,
            compressed_size=comp_size,
            encrypted_size=enc_res.encrypted_size,
            nonce_hex=enc_res.nonce_hex,
            auth_tag_hex=enc_res.auth_tag_hex,
            compression_algorithm="zlib",
            encryption_algorithm="AES-256-GCM",
        )

        # Stamp CLEAN scan result on the version record
        version.scan_status = scan_result.status.value
        version.scan_timestamp = scan_result.scanned_at
        await self.db.commit()

        # 7. Publish Module 3 Hook
        await publish_backup_completed_event({
            "version_id": str(version.id),
            "file_id": str(file_record.id),
            "organization_id": str(organization_id) if organization_id else None,
            "device_id": str(device_id),
            "file_path": file_record.file_path,
            "version_number": version.version_number,
            "file_hash_sha256": version.file_hash_sha256,
            "storage_path": version.storage_path,
            "original_size_bytes": version.original_size_bytes,
            "encrypted_size_bytes": version.size_bytes,
        })

        return version

    async def manual_backup(
        self,
        manual_in: ManualBackupRequest,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> FileVersionResponse:
        """Execute immediate file backup via base64 upload payload."""
        device = await self.device_repo.get_by_id(manual_in.device_id)
        if not device:
            raise EntityNotFoundException("Device", manual_in.device_id)

        self._assert_device_owner(device, current_user)
        await self._validate_protected_folder(device.id, manual_in.protected_folder_id)

        try:
            raw_bytes = base64.b64decode(manual_in.file_content_base64)
        except Exception:
            raise VaultGuardException("Invalid base64 payload in file_content_base64")

        # Create quick job record for tracking
        job = await self.repository.create_job(
            organization_id=device.organization_id,
            device_id=device.id,
            job_type="MANUAL",
        )

        try:
            version = await self.process_file_backup(
                organization_id=device.organization_id,
                device_id=device.id,
                file_path=manual_in.file_path,
                raw_bytes=raw_bytes,
                protected_folder_id=manual_in.protected_folder_id,
                job_id=job.id,
                user_id=current_user.id,
            )

            await self.repository.complete_job(
                job=job,
                status="COMPLETED",
                total_files=1,
                bytes_processed=len(raw_bytes),
                files_failed=0,
            )

            await self.audit_service.log(
                action="MANUAL_BACKUP_COMPLETED",
                resource_type="FileVersion",
                resource_id=str(version.id),
                organization_id=device.organization_id,
                user_id=current_user.id,
                details={
                    "file_path": manual_in.file_path,
                    "version_number": version.version_number,
                    "sha256": version.file_hash_sha256,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return FileVersionResponse.model_validate(version)

        except Exception as e:
            await self.repository.complete_job(
                job=job,
                status="FAILED",
                total_files=1,
                bytes_processed=0,
                files_failed=1,
                error_message=str(e),
            )
            raise

    async def manual_backup_bytes(
        self,
        device_id: uuid.UUID,
        file_path: str,
        raw_bytes: bytes,
        current_user: User,
        protected_folder_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> FileVersionResponse:
        """Execute immediate file backup from raw bytes (multipart upload path).

        Called by the ``POST /backups/manual`` endpoint which accepts
        ``multipart/form-data`` instead of a base64 JSON body, avoiding the
        ~33 % size inflation that caused HTTP 413 for files over ~750 KB.
        """
        device = await self.device_repo.get_by_id(device_id)
        if not device:
            raise EntityNotFoundException("Device", device_id)

        self._assert_device_owner(device, current_user)
        await self._validate_protected_folder(device.id, protected_folder_id)

        job = await self.repository.create_job(
            organization_id=device.organization_id,
            device_id=device.id,
            job_type="MANUAL",
        )

        try:
            version = await self.process_file_backup(
                organization_id=device.organization_id,
                device_id=device.id,
                file_path=file_path,
                raw_bytes=raw_bytes,
                protected_folder_id=protected_folder_id,
                job_id=job.id,
                user_id=current_user.id,
            )

            await self.repository.complete_job(
                job=job,
                status="COMPLETED",
                total_files=1,
                bytes_processed=len(raw_bytes),
                files_failed=0,
            )

            await self.audit_service.log(
                action="MANUAL_BACKUP_COMPLETED",
                resource_type="FileVersion",
                resource_id=str(version.id),
                organization_id=device.organization_id,
                user_id=current_user.id,
                details={
                    "file_path": file_path,
                    "version_number": version.version_number,
                    "sha256": version.file_hash_sha256,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )

            return FileVersionResponse.model_validate(version)

        except Exception as e:
            await self.repository.complete_job(
                job=job,
                status="FAILED",
                total_files=1,
                bytes_processed=0,
                files_failed=1,
                error_message=str(e),
            )
            raise

    async def list_jobs(
        self,
        current_user: User,
        device_id: Optional[uuid.UUID] = None,
        owner_scope: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[BackupJobResponse], int]:
        device_ids = await self._visible_device_ids(current_user, owner_scope)
        if device_id and device_id not in device_ids:
            return [], 0

        jobs, total = await self.repository.list_jobs(
            device_ids=None if device_id else device_ids,
            device_id=device_id,
            status=status,
            skip=skip,
            limit=limit,
        )
        return [BackupJobResponse.model_validate(j) for j in jobs], total

    async def list_snapshots(
        self,
        current_user: User,
        device_id: Optional[uuid.UUID] = None,
        owner_scope: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[BackupSnapshotResponse], int]:
        device_ids = await self._visible_device_ids(current_user, owner_scope)
        if device_id and device_id not in device_ids:
            return [], 0

        snapshots, total = await self.repository.list_recent_snapshots(
            device_id=device_id,
            device_ids=None if device_id else device_ids,
            skip=skip,
            limit=limit,
        )
        return [BackupSnapshotResponse(**s) for s in snapshots], total

    async def get_file_history(
        self,
        file_id: uuid.UUID,
        current_user: User,
    ) -> FileHistoryItem:
        allowed_device_ids = await self._visible_device_ids(current_user)
        file_record = await self.repository.get_file_history(
            file_id=file_id,
            device_ids=allowed_device_ids,
        )
        if not file_record:
            raise EntityNotFoundException("File", file_id)

        return FileHistoryItem.model_validate(file_record)

    def _assert_employee_dashboard_admin(self, current_user: User) -> uuid.UUID:
        if (
            current_user.role.name != RoleType.ADMIN.value
            or current_user.organization_id is None
        ):
            raise AuthorizationException(
                "Only organization administrators can view employee backup details."
            )
        return current_user.organization_id

    async def _get_employee_in_admin_organization(
        self,
        employee_id: uuid.UUID,
        current_user: User,
    ) -> User:
        organization_id = self._assert_employee_dashboard_admin(current_user)
        result = await self.db.execute(
            select(User)
            .join(Role, User.role_id == Role.id)
            .options(selectinload(User.role))
            .where(
                User.id == employee_id,
                User.organization_id == organization_id,
                Role.name == RoleType.EMPLOYEE.value,
            )
        )
        employee = result.scalar_one_or_none()
        if not employee:
            raise EntityNotFoundException("Employee", employee_id)
        return employee

    async def _employee_backup_stats(
        self,
        employee_ids: List[uuid.UUID],
        organization_id: uuid.UUID,
    ) -> Dict[uuid.UUID, Dict[str, Any]]:
        if not employee_ids:
            return {}

        file_org_scope = or_(
            File.organization_id == organization_id,
            File.organization_id.is_(None),
        )
        result = await self.db.execute(
            select(
                Device.user_id,
                func.count(func.distinct(File.id)).label("total_backup_files"),
                func.coalesce(func.sum(FileVersion.size_bytes), 0).label(
                    "storage_used_bytes"
                ),
                func.max(FileVersion.created_at).label("last_backup_at"),
            )
            .select_from(Device)
            .outerjoin(
                File,
                and_(
                    File.device_id == Device.id,
                    file_org_scope,
                ),
            )
            .outerjoin(FileVersion, FileVersion.file_id == File.id)
            .where(
                Device.user_id.in_(employee_ids),
                Device.organization_id == organization_id,
            )
            .group_by(Device.user_id)
        )
        return {
            row.user_id: {
                "total_backup_files": int(row.total_backup_files or 0),
                "storage_used_bytes": int(row.storage_used_bytes or 0),
                "last_backup_at": row.last_backup_at,
            }
            for row in result.all()
            if row.user_id is not None
        }

    async def _latest_employee_job_statuses(
        self,
        employee_ids: List[uuid.UUID],
        organization_id: uuid.UUID,
    ) -> Dict[uuid.UUID, str]:
        if not employee_ids:
            return {}

        result = await self.db.execute(
            select(BackupJob.status, Device.user_id)
            .join(Device, BackupJob.device_id == Device.id)
            .where(
                Device.user_id.in_(employee_ids),
                Device.organization_id == organization_id,
                BackupJob.organization_id == organization_id,
            )
            .order_by(desc(BackupJob.created_at))
        )
        statuses: Dict[uuid.UUID, str] = {}
        for status, user_id in result.all():
            if user_id is not None and user_id not in statuses:
                statuses[user_id] = status
        return statuses

    async def list_employee_backup_summaries(
        self,
        current_user: User,
    ) -> List[EmployeeBackupSummary]:
        organization_id = self._assert_employee_dashboard_admin(current_user)
        result = await self.db.execute(
            select(User)
            .join(Role, User.role_id == Role.id)
            .options(selectinload(User.role))
            .where(
                User.organization_id == organization_id,
                Role.name == RoleType.EMPLOYEE.value,
            )
            .order_by(User.full_name, User.email)
        )
        employees = list(result.scalars().all())
        employee_ids = [employee.id for employee in employees]
        stats = await self._employee_backup_stats(employee_ids, organization_id)
        latest_statuses = await self._latest_employee_job_statuses(
            employee_ids, organization_id
        )

        summaries = []
        for employee in employees:
            employee_stats = stats.get(
                employee.id,
                {
                    "total_backup_files": 0,
                    "storage_used_bytes": 0,
                    "last_backup_at": None,
                },
            )
            total_files = employee_stats["total_backup_files"]
            status = latest_statuses.get(
                employee.id,
                "COMPLETED" if total_files else "NO_BACKUPS",
            )
            summaries.append(
                EmployeeBackupSummary(
                    employee_id=employee.id,
                    full_name=employee.full_name,
                    email=employee.email,
                    is_active=employee.is_active,
                    created_at=employee.created_at,
                    total_backup_files=total_files,
                    storage_used_bytes=employee_stats["storage_used_bytes"],
                    last_backup_at=employee_stats["last_backup_at"],
                    backup_status=status,
                )
            )
        return summaries

    async def get_employee_backup_details(
        self,
        employee_id: uuid.UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
        recovery_skip: int = 0,
        recovery_limit: int = 50,
    ) -> EmployeeBackupDetails:
        employee = await self._get_employee_in_admin_organization(
            employee_id, current_user
        )
        organization_id = self._assert_employee_dashboard_admin(current_user)
        device_result = await self.db.execute(
            select(Device.id).where(
                Device.user_id == employee.id,
                Device.organization_id == organization_id,
            )
        )
        device_ids = list(device_result.scalars().all())
        stats = await self._employee_backup_stats([employee.id], organization_id)
        employee_stats = stats.get(
            employee.id,
            {
                "total_backup_files": 0,
                "storage_used_bytes": 0,
                "last_backup_at": None,
            },
        )
        latest_statuses = await self._latest_employee_job_statuses(
            [employee.id], organization_id
        )
        total_files = employee_stats["total_backup_files"]
        backup_status = latest_statuses.get(
            employee.id,
            "COMPLETED" if total_files else "NO_BACKUPS",
        )

        file_scope = (
            File.device_id.in_(device_ids),
            or_(
                File.organization_id == organization_id,
                File.organization_id.is_(None),
            ),
        )
        count_result = await self.db.execute(
            select(func.count(File.id)).where(*file_scope)
        )
        files_total = count_result.scalar_one() or 0
        file_result = await self.db.execute(
            select(File)
            .options(selectinload(File.versions))
            .where(*file_scope)
            .order_by(desc(File.updated_at), File.id)
            .offset(skip)
            .limit(limit)
        )
        files = []
        for file_record in file_result.scalars().all():
            versions = sorted(
                file_record.versions,
                key=lambda version: version.version_number,
            )
            files.append(
                EmployeeBackupFile(
                    id=file_record.id,
                    file_path=file_record.file_path,
                    original_filename=file_record.original_filename,
                    file_size=file_record.file_size,
                    total_versions=file_record.total_versions,
                    is_deleted=file_record.is_deleted,
                    created_at=file_record.created_at,
                    updated_at=file_record.updated_at,
                    versions=[
                        EmployeeBackupVersion(
                            id=version.id,
                            version_number=version.version_number,
                            original_size_bytes=version.original_size_bytes,
                            encrypted_size_bytes=version.size_bytes,
                            file_hash_sha256=version.file_hash_sha256,
                            is_encrypted=version.is_encrypted,
                            encryption_algorithm=version.encryption_algorithm,
                            created_at=version.created_at,
                        )
                        for version in versions
                    ],
                )
            )

        employee_recovery_job_ids = (
            select(RecoveryJobItem.recovery_job_id)
            .join(File, RecoveryJobItem.file_id == File.id)
            .where(
                File.device_id.in_(device_ids),
                or_(
                    File.organization_id == organization_id,
                    File.organization_id.is_(None),
                ),
            )
            .distinct()
        )
        cross_employee_recovery_job_ids = (
            select(RecoveryJobItem.recovery_job_id)
            .join(File, RecoveryJobItem.file_id == File.id)
            .where(
                or_(
                    File.device_id.not_in(device_ids),
                    and_(
                        File.organization_id.is_not(None),
                        File.organization_id != organization_id,
                    ),
                )
            )
            .distinct()
        )
        recovery_job_scope = (
            RecoveryJob.organization_id == organization_id,
            RecoveryJob.requested_by_id == employee.id,
            RecoveryJob.id.in_(employee_recovery_job_ids),
            ~RecoveryJob.id.in_(cross_employee_recovery_job_ids),
        )
        recovery_result = await self.db.execute(
            select(RecoveryJob)
            .where(*recovery_job_scope)
            .order_by(desc(RecoveryJob.created_at))
            .offset(recovery_skip)
            .limit(recovery_limit)
        )
        recovery_count_result = await self.db.execute(
            select(func.count(RecoveryJob.id)).where(*recovery_job_scope)
        )
        recovery_total = recovery_count_result.scalar_one() or 0
        recovery_history = [
            EmployeeRecoveryHistoryItem(
                id=job.id,
                job_type=job.job_type,
                status=job.status,
                total_files=job.total_files,
                files_restored=job.files_restored,
                files_failed=job.files_failed,
                bytes_restored=job.bytes_restored,
                started_at=job.started_at,
                completed_at=job.completed_at,
                created_at=job.created_at,
            )
            for job in recovery_result.scalars().all()
        ]

        return EmployeeBackupDetails(
            employee=EmployeeBackupProfile(
                id=employee.id,
                full_name=employee.full_name,
                email=employee.email,
                organization_id=employee.organization_id,
                is_active=employee.is_active,
                is_verified=employee.is_verified,
                created_at=employee.created_at,
            ),
            total_backup_files=total_files,
            storage_used_bytes=employee_stats["storage_used_bytes"],
            last_backup_at=employee_stats["last_backup_at"],
            backup_status=backup_status,
            files=PaginatedResponse[EmployeeBackupFile](
                items=files,
                total=files_total,
                skip=skip,
                limit=limit,
            ),
            recovery_history=PaginatedResponse[EmployeeRecoveryHistoryItem](
                items=recovery_history,
                total=recovery_total,
                skip=recovery_skip,
                limit=recovery_limit,
            ),
        )

