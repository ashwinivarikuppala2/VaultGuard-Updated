import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.device import Device
from app.models.future_placeholders import BackupJob, File, FileVersion
from app.models.protected_folder import ProtectedFolder


class BackupRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Backup Jobs ====================
    async def create_job(
        self,
        organization_id: Optional[uuid.UUID] = None,
        device_id: Optional[uuid.UUID] = None,
        job_type: str = "FULL",
    ) -> BackupJob:
        job = BackupJob(
            organization_id=organization_id,
            device_id=device_id,
            job_type=job_type,
            status="IN_PROGRESS",
            started_at=datetime.now(timezone.utc),
            total_files=0,
            bytes_processed=0,
            files_failed=0,
            files_skipped=0,
            duration_seconds=0.0,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_job_by_id(self, job_id: uuid.UUID) -> Optional[BackupJob]:
        query = select(BackupJob).where(BackupJob.id == job_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        organization_id: Optional[uuid.UUID] = None,
        device_id: Optional[uuid.UUID] = None,
        device_ids: Optional[List[uuid.UUID]] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[BackupJob], int]:
        total_query = select(func.count()).select_from(BackupJob)
        query = select(BackupJob).order_by(desc(BackupJob.created_at))

        if organization_id:
            total_query = total_query.where(BackupJob.organization_id == organization_id)
            query = query.where(BackupJob.organization_id == organization_id)
        if device_id:
            total_query = total_query.where(BackupJob.device_id == device_id)
            query = query.where(BackupJob.device_id == device_id)
        elif device_ids is not None:
            total_query = total_query.where(BackupJob.device_id.in_(device_ids))
            query = query.where(BackupJob.device_id.in_(device_ids))
        if status:
            total_query = total_query.where(BackupJob.status == status)
            query = query.where(BackupJob.status == status)

        total_res = await self.db.execute(total_query)
        total = total_res.scalar_one() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def complete_job(
        self,
        job: BackupJob,
        status: str,
        total_files: int,
        bytes_processed: int,
        files_failed: int = 0,
        files_skipped: int = 0,
        error_message: Optional[str] = None,
    ) -> BackupJob:
        now = datetime.now(timezone.utc)
        job.completed_at = now
        job.status = status
        job.total_files = total_files
        job.bytes_processed = bytes_processed
        job.files_failed = files_failed
        job.files_skipped = files_skipped
        job.error_message = error_message
        if job.started_at:
            started_at = job.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            job.duration_seconds = round((now - started_at).total_seconds(), 2)

        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    # ==================== Files & Versions ====================
    async def get_or_create_file(
        self,
        organization_id: Optional[uuid.UUID],
        device_id: uuid.UUID,
        file_path: str,
        protected_folder_id: Optional[uuid.UUID] = None,
    ) -> File:
        query = select(File).where(
            File.device_id == device_id,
            File.file_path == file_path,
        )
        if organization_id:
            query = query.where(File.organization_id == organization_id)
        else:
            query = query.where(File.organization_id.is_(None))
        result = await self.db.execute(query)
        file_record = result.scalar_one_or_none()

        if not file_record:
            filename = os.path.basename(file_path) or file_path
            file_record = File(
                organization_id=organization_id,
                device_id=device_id,
                file_path=file_path,
                original_filename=filename,
                file_size=0,
                total_versions=0,
                protected_folder_id=protected_folder_id,
                is_deleted=False,
            )
            self.db.add(file_record)
            await self.db.flush()
            await self.db.refresh(file_record)

        return file_record

    async def create_file_version(
        self,
        file_record: File,
        storage_path: str,
        file_hash_sha256: str,
        original_size: int,
        compressed_size: int,
        encrypted_size: int,
        nonce_hex: str,
        auth_tag_hex: str,
        compression_algorithm: str = "zlib",
        encryption_algorithm: str = "AES-256-GCM",
    ) -> FileVersion:
        new_version_number = file_record.total_versions + 1

        version = FileVersion(
            file_id=file_record.id,
            version_number=new_version_number,
            storage_path=storage_path,
            file_hash_sha256=file_hash_sha256,
            size_bytes=encrypted_size,
            original_size_bytes=original_size,
            compressed_size_bytes=compressed_size,
            compression_algorithm=compression_algorithm,
            encryption_algorithm=encryption_algorithm,
            nonce_hex=nonce_hex,
            auth_tag_hex=auth_tag_hex,
            is_encrypted=True,
            is_quarantined=False,
        )
        self.db.add(version)

        # Update file master record
        file_record.file_size = original_size
        file_record.total_versions = new_version_number
        file_record.is_deleted = False
        self.db.add(file_record)

        await self.db.flush()
        await self.db.refresh(version)
        return version

    async def get_file_history(
        self,
        file_id: uuid.UUID,
        device_ids: Optional[List[uuid.UUID]] = None,
    ) -> Optional[File]:
        query = (
            select(File)
            .options(selectinload(File.versions))
            .where(File.id == file_id)
        )
        if device_ids is not None:
            query = query.where(File.device_id.in_(device_ids))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_recent_snapshots(
        self,
        organization_id: Optional[uuid.UUID] = None,
        device_id: Optional[uuid.UUID] = None,
        device_ids: Optional[List[uuid.UUID]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        total_query = (
            select(func.count(FileVersion.id))
            .select_from(FileVersion)
            .join(File, FileVersion.file_id == File.id)
        )
        query = (
            select(
                FileVersion.id.label("version_id"),
                File.id.label("file_id"),
                File.file_path,
                File.original_filename,
                FileVersion.version_number,
                FileVersion.file_hash_sha256,
                FileVersion.original_size_bytes,
                FileVersion.size_bytes.label("encrypted_size_bytes"),
                FileVersion.storage_path,
                FileVersion.created_at,
            )
            .join(File, FileVersion.file_id == File.id)
            .order_by(desc(FileVersion.created_at))
        )

        if organization_id:
            total_query = total_query.where(File.organization_id == organization_id)
            query = query.where(File.organization_id == organization_id)
        if device_id:
            total_query = total_query.where(File.device_id == device_id)
            query = query.where(File.device_id == device_id)
        elif device_ids is not None:
            total_query = total_query.where(File.device_id.in_(device_ids))
            query = query.where(File.device_id.in_(device_ids))

        total_res = await self.db.execute(total_query)
        total = total_res.scalar_one() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        rows = result.mappings().all()
        return [dict(row) for row in rows], total

    # ==================== Storage Analytics ====================
    async def get_storage_statistics(
        self,
        organization_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        device_ids: Optional[List[uuid.UUID]] = None,
    ) -> Dict[str, Any]:
        # File counts
        files_q = select(func.count(File.id)).select_from(File)
        versions_q = select(
            func.count(FileVersion.id),
            func.coalesce(func.sum(FileVersion.original_size_bytes), 0),
            func.coalesce(func.sum(FileVersion.size_bytes), 0),
        ).select_from(FileVersion).join(File, FileVersion.file_id == File.id)

        folders_q = select(func.count(ProtectedFolder.id)).select_from(ProtectedFolder).where(ProtectedFolder.is_active == True)
        jobs_q = select(
            func.count(BackupJob.id),
            func.coalesce(func.sum(case((BackupJob.status == "COMPLETED", 1), else_=0)), 0),
            func.coalesce(func.sum(case((BackupJob.status == "FAILED", 1), else_=0)), 0),
        ).select_from(BackupJob)

        dev_query = (
            select(
                Device.id.label("device_id"),
                Device.name.label("device_name"),
                func.count(func.distinct(File.id)).label("total_files"),
                func.count(FileVersion.id).label("total_versions"),
                func.coalesce(func.sum(FileVersion.size_bytes), 0).label("total_bytes"),
            )
            .outerjoin(File, Device.id == File.device_id)
            .outerjoin(FileVersion, File.id == FileVersion.file_id)
            .group_by(Device.id, Device.name)
        )

        if user_id:
            files_q = files_q.join(Device, File.device_id == Device.id).where(Device.user_id == user_id)
            versions_q = versions_q.join(Device, File.device_id == Device.id).where(Device.user_id == user_id)
            folders_q = folders_q.join(Device, ProtectedFolder.device_id == Device.id).where(Device.user_id == user_id)
            jobs_q = jobs_q.join(Device, BackupJob.device_id == Device.id).where(Device.user_id == user_id)
            dev_query = dev_query.where(Device.user_id == user_id)
        elif organization_id:
            files_q = files_q.where(File.organization_id == organization_id)
            versions_q = versions_q.where(File.organization_id == organization_id)
            folders_q = folders_q.where(ProtectedFolder.organization_id == organization_id)
            jobs_q = jobs_q.where(BackupJob.organization_id == organization_id)
            dev_query = dev_query.where(Device.organization_id == organization_id)
        elif device_ids is not None:
            files_q = files_q.join(Device, File.device_id == Device.id).where(Device.id.in_(device_ids))
            versions_q = versions_q.join(Device, File.device_id == Device.id).where(Device.id.in_(device_ids))
            folders_q = folders_q.join(Device, ProtectedFolder.device_id == Device.id).where(Device.id.in_(device_ids))
            jobs_q = jobs_q.join(Device, BackupJob.device_id == Device.id).where(Device.id.in_(device_ids))
            dev_query = dev_query.where(Device.id.in_(device_ids))

        files_res = await self.db.execute(files_q)
        total_files = files_res.scalar_one() or 0

        ver_res = await self.db.execute(versions_q)
        ver_row = ver_res.first()
        total_versions = ver_row[0] if ver_row else 0
        total_orig_bytes = ver_row[1] if ver_row else 0
        total_stored_bytes = ver_row[2] if ver_row else 0

        folders_res = await self.db.execute(folders_q)
        active_folders = folders_res.scalar_one() or 0

        jobs_res = await self.db.execute(jobs_q)
        jobs_row = jobs_res.first()
        total_jobs = jobs_row[0] if jobs_row else 0
        success_jobs = jobs_row[1] if jobs_row else 0
        failed_jobs = jobs_row[2] if jobs_row else 0

        space_saved = max(0, total_orig_bytes - total_stored_bytes)
        savings_pct = round((space_saved / total_orig_bytes * 100), 2) if total_orig_bytes > 0 else 0.0

        dev_res = await self.db.execute(dev_query)
        device_breakdown = [dict(r) for r in dev_res.mappings().all()]

        return {
            "total_files": total_files,
            "total_versions": total_versions,
            "total_original_bytes": total_orig_bytes,
            "total_stored_bytes": total_stored_bytes,
            "space_saved_bytes": space_saved,
            "compression_savings_percent": savings_pct,
            "active_protected_folders": active_folders,
            "total_backup_jobs": total_jobs,
            "successful_backup_jobs": success_jobs,
            "failed_backup_jobs": failed_jobs,
            "device_breakdown": device_breakdown,
        }

