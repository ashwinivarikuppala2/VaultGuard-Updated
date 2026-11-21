import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_log import AuditLog
from app.models.device import Device, DeviceStatus
from app.models.future_placeholders import File, FileVersion
from app.models.role import RoleType
from app.models.recovery import (
    ApprovalRequest,
    DestinationType,
    OverwritePolicy,
    RecoveryItemStatus,
    RecoveryJob,
    RecoveryJobItem,
    RecoveryJobStatus,
    RecoveryJobType,
    ThreatRiskLabel,
)
from app.models.threat import ThreatLevel
from app.models.user import User
from app.services.alerts.alert_service import alert_service
from app.services.recovery.integrity_service import IntegrityVerificationError, integrity_service
from app.services.recovery.path_validator import PathValidationError, path_validator
from app.services.recovery.risk_assessor import risk_assessor

logger = logging.getLogger("vaultguard.recovery.service")


class RecoveryService:
    """Master orchestrator for single-file, folder, bulk, and point-in-time restoration."""

    async def get_verified_item_payload(
        self,
        db: AsyncSession,
        job: RecoveryJob,
        item: RecoveryJobItem,
    ) -> bytes:
        if item.recovery_job_id != job.id:
            raise ValueError("Recovery item does not belong to this job.")

        payload_res = await db.execute(
            select(FileVersion, File, Device)
            .join(File, FileVersion.file_id == File.id)
            .join(Device, File.device_id == Device.id)
            .where(
                FileVersion.id == item.file_version_id,
                FileVersion.file_id == item.file_id,
            )
        )
        payload_row = payload_res.first()
        if not payload_row:
            raise ValueError("Recovery item version does not belong to its file.")
        version, file_record, device = payload_row

        if job.target_device_id and job.target_device_id != device.id:
            raise ValueError("Recovery item does not belong to the job's target device.")
        if (
            file_record.organization_id != job.organization_id
            or device.organization_id != job.organization_id
        ):
            raise ValueError("Recovery item does not belong to the job's organization.")

        requester_res = await db.execute(
            select(User)
            .options(selectinload(User.role))
            .where(User.id == job.requested_by_id)
        )
        requester = requester_res.scalar_one_or_none()
        if not requester or requester.role.name not in (
            RoleType.ADMIN.value,
            RoleType.EMPLOYEE.value,
            RoleType.INDIVIDUAL.value,
        ):
            raise ValueError("Recovery job requester is not valid.")
        if device.user_id != requester.id:
            raise ValueError("Recovery job requester does not own the restored file.")

        if job.organization_id:
            tenant_key = str(job.organization_id)
        else:
            tenant_key = f"personal-{requester.id}"

        plaintext, _ = integrity_service.restore_and_verify_payload(
            version=version,
            organization_id=tenant_key,
            associated_data=item.original_path.encode("utf-8"),
        )
        return plaintext

    async def preview_restore(
        self,
        db: AsyncSession,
        organization_id: Optional[uuid.UUID],
        job_type: str,
        file_version_ids: Optional[List[uuid.UUID]] = None,
        folder_path: Optional[str] = None,
        device_id: Optional[uuid.UUID] = None,
        device_ids: Optional[List[uuid.UUID]] = None,
        point_in_time: Optional[datetime] = None,
        destination_path: Optional[str] = None,
        destination_type: str = DestinationType.SAFE_DIR.value,
        overwrite_policy: str = OverwritePolicy.SKIP.value,
    ) -> Dict[str, Any]:
        """
        Validates target versions, computes threat risk ratings, and inspects destination collisions
        prior to executing a recovery job.
        """
        candidate_versions: List[FileVersion] = []

        if job_type == RecoveryJobType.SINGLE_FILE.value:
            if not file_version_ids or len(file_version_ids) != 1:
                raise ValueError("Single-file restore requires exactly one file_version_id.")
            q = select(FileVersion).join(File).where(FileVersion.id == file_version_ids[0])
            if device_ids is not None:
                q = q.where(File.device_id.in_(device_ids))
            if organization_id is not None:
                q = q.where(File.organization_id == organization_id)
            v_res = await db.execute(q)
            v = v_res.scalar_one_or_none()
            if not v:
                raise ValueError("Selected file version not found or access denied.")
            candidate_versions = [v]

        elif job_type == RecoveryJobType.BULK.value:
            if not file_version_ids:
                raise ValueError("Bulk restore requires at least one file_version_id.")
            q = select(FileVersion).join(File).where(FileVersion.id.in_(file_version_ids))
            if device_ids is not None:
                q = q.where(File.device_id.in_(device_ids))
            if organization_id is not None:
                q = q.where(File.organization_id == organization_id)
            v_res = await db.execute(q)
            candidate_versions = list(v_res.scalars().all())
            if len(candidate_versions) != len(file_version_ids):
                raise ValueError("One or more selected file versions were not found or are not accessible.")

        elif job_type == RecoveryJobType.FOLDER.value:
            if not folder_path:
                raise ValueError("Folder restore requires folder_path.")
            norm_prefix = folder_path.replace("\\", "/").rstrip("/") + "/"
            file_query = select(File).where(
                File.file_path.startswith(norm_prefix),
                File.is_deleted == False,
            )
            if device_ids is not None:
                file_query = file_query.where(File.device_id.in_(device_ids))
            if organization_id is not None:
                file_query = file_query.where(File.organization_id == organization_id)
            if device_id:
                file_query = file_query.where(File.device_id == device_id)
            f_res = await db.execute(file_query)
            files = f_res.scalars().all()
            for f in files:
                latest_v = await db.execute(
                    select(FileVersion)
                    .where(FileVersion.file_id == f.id)
                    .order_by(desc(FileVersion.version_number))
                    .limit(1)
                )
                v = latest_v.scalar_one_or_none()
                if v:
                    candidate_versions.append(v)

        elif job_type == RecoveryJobType.POINT_IN_TIME.value:
            if not point_in_time:
                raise ValueError("Point-in-time recovery requires a snapshot timestamp.")
            file_query = select(File).where(File.is_deleted == False)
            if device_ids is not None:
                file_query = file_query.where(File.device_id.in_(device_ids))
            if organization_id is not None:
                file_query = file_query.where(File.organization_id == organization_id)
            if device_id:
                file_query = file_query.where(File.device_id == device_id)
            f_res = await db.execute(file_query)
            files = f_res.scalars().all()

            for f in files:
                pit_v = await db.execute(
                    select(FileVersion)
                    .where(
                        FileVersion.file_id == f.id,
                        FileVersion.created_at <= point_in_time,
                    )
                    .order_by(desc(FileVersion.created_at))
                    .limit(1)
                )
                v = pit_v.scalar_one_or_none()
                if v:
                    candidate_versions.append(v)

        # Inspect candidate versions and perform risk assessments
        items_preview = []
        risk_counts = {
            ThreatRiskLabel.NO_KNOWN_THREAT.value: 0,
            ThreatRiskLabel.POTENTIALLY_SUSPICIOUS.value: 0,
            ThreatRiskLabel.INSUFFICIENT_DATA.value: 0,
        }
        total_bytes = 0
        conflicts = 0

        for v in candidate_versions:
            f_res = await db.execute(select(File).where(File.id == v.file_id))
            f = f_res.scalar_one()

            # Risk Assessment
            assessment = await risk_assessor.assess_version_risk(db=db, version=v, file=f)
            risk_counts[assessment.risk_label] = risk_counts.get(assessment.risk_label, 0) + 1
            total_bytes += (v.original_size_bytes or v.size_bytes)

            # Destination resolution & conflict preview
            target_dest = path_validator.validate_and_resolve_destination(
                original_file_path=f.file_path,
                destination_path=destination_path,
                destination_type=destination_type,
                organization_id=str(organization_id),
            )
            has_conflict = os.path.exists(target_dest)
            if has_conflict:
                conflicts += 1

            items_preview.append({
                "file_id": str(f.id),
                "file_version_id": str(v.id),
                "original_path": f.file_path,
                "target_path": target_dest,
                "size_bytes": v.original_size_bytes or v.size_bytes,
                "version_number": v.version_number,
                "created_at": v.created_at.isoformat(),
                "has_conflict": has_conflict,
                "risk_assessment": assessment.to_dict(),
            })

        # Dual-custody requirement heuristic: bulk restores > 10 files or restore of suspicious versions
        requires_approval = (len(candidate_versions) > 10) or (risk_counts[ThreatRiskLabel.POTENTIALLY_SUSPICIOUS.value] > 0)

        return {
            "job_type": job_type,
            "total_files": len(items_preview),
            "total_bytes": total_bytes,
            "conflicts_count": conflicts,
            "risk_summary": risk_counts,
            "requires_approval": requires_approval,
            "items": items_preview,
        }

    async def create_recovery_job(
        self,
        db: AsyncSession,
        organization_id: Optional[uuid.UUID],
        requested_by_id: uuid.UUID,
        job_type: str,
        file_version_ids: Optional[List[uuid.UUID]] = None,
        folder_path: Optional[str] = None,
        device_id: Optional[uuid.UUID] = None,
        device_ids: Optional[List[uuid.UUID]] = None,
        snapshot_time: Optional[datetime] = None,
        destination_path: Optional[str] = None,
        destination_type: str = DestinationType.SAFE_DIR.value,
        overwrite_policy: str = OverwritePolicy.SKIP.value,
        bypass_approval_check: bool = False,
    ) -> RecoveryJob:
        """
        Creates a persistent RecoveryJob and associated RecoveryJobItem records.
        """
        preview = await self.preview_restore(
            db=db,
            organization_id=organization_id,
            job_type=job_type,
            file_version_ids=file_version_ids,
            folder_path=folder_path,
            device_id=device_id,
            device_ids=device_ids,
            point_in_time=snapshot_time,
            destination_path=destination_path,
            destination_type=destination_type,
            overwrite_policy=overwrite_policy,
        )

        requires_approval = preview["requires_approval"] and not bypass_approval_check
        approval_id: Optional[uuid.UUID] = None

        if requires_approval:
            # Create ApprovalRequest for dual-custody authorization
            approval = ApprovalRequest(
                organization_id=organization_id,
                requested_by_id=requested_by_id,
                request_type=f"RECOVERY_{job_type}",
                status="PENDING",
                payload={
                    "job_type": job_type,
                    "total_files": preview["total_files"],
                    "total_bytes": preview["total_bytes"],
                    "risk_summary": preview["risk_summary"],
                },
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
            db.add(approval)
            await db.flush()
            approval_id = approval.id

        # Create Master RecoveryJob
        job = RecoveryJob(
            organization_id=organization_id,
            target_device_id=device_id,
            requested_by_id=requested_by_id,
            job_type=job_type,
            status=RecoveryJobStatus.PENDING.value,
            snapshot_time=snapshot_time,
            destination_path=destination_path or "recovered_files",
            destination_type=destination_type,
            overwrite_policy=overwrite_policy,
            total_files=len(preview["items"]),
            files_restored=0,
            files_failed=0,
            files_skipped=0,
            bytes_restored=0,
            requires_approval=requires_approval,
            approval_request_id=approval_id,
            risk_assessment=preview["risk_summary"],
        )
        db.add(job)
        await db.flush()

        # Create Item records
        for item in preview["items"]:
            job_item = RecoveryJobItem(
                recovery_job_id=job.id,
                file_id=uuid.UUID(item["file_id"]),
                file_version_id=uuid.UUID(item["file_version_id"]),
                original_path=item["original_path"],
                target_path=item["target_path"],
                status=RecoveryItemStatus.PENDING.value,
                threat_status=item["risk_assessment"]["risk_label"],
                threat_rationale=item["risk_assessment"]["rationale"],
            )
            db.add(job_item)

        # Audit Log
        audit = AuditLog(
            organization_id=organization_id,
            user_id=requested_by_id,
            action="RECOVERY_JOB_CREATED",
            resource_type="RecoveryJob",
            resource_id=str(job.id),
            details={
                "job_id": str(job.id),
                "job_type": job_type,
                "total_files": len(preview["items"]),
                "requires_approval": requires_approval,
                "overwrite_policy": overwrite_policy,
                "destination_type": destination_type,
            },
        )
        db.add(audit)
        await db.commit()
        await db.refresh(job)

        logger.info(f"RecoveryJob {job.id} created with {job.total_files} items (requires_approval={requires_approval})")
        return job

    async def execute_recovery_job(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
    ) -> RecoveryJob:
        """
        Executes recovery items sequentially with cryptographic integrity checks
        and atomic safe-staging writes.
        """
        res = await db.execute(
            select(RecoveryJob)
            .where(RecoveryJob.id == job_id)
            .options(selectinload(RecoveryJob.items))
        )
        job = res.scalar_one_or_none()
        if not job:
            raise ValueError(f"Recovery job {job_id} not found.")

        if job.status in (RecoveryJobStatus.COMPLETED.value, RecoveryJobStatus.CANCELLED.value):
            return job

        if job.requires_approval and job.approval_request_id:
            app_res = await db.execute(select(ApprovalRequest).where(ApprovalRequest.id == job.approval_request_id))
            approval = app_res.scalar_one_or_none()
            if not approval or approval.status != "APPROVED":
                job.status = RecoveryJobStatus.FAILED.value
                job.error_message = "Recovery execution rejected: Pending dual-custody authorization."
                await db.commit()
                return job

        # Begin execution
        job.status = RecoveryJobStatus.IN_PROGRESS.value
        job.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Audit Log: Recovery Started
        db.add(AuditLog(
            organization_id=job.organization_id,
            user_id=job.requested_by_id,
            action="RECOVERY_JOB_STARTED",
            resource_type="RecoveryJob",
            resource_id=str(job.id),
            details={"job_id": str(job.id), "total_files": job.total_files},
        ))
        await db.commit()

        for item in job.items:
            # Check for cancellation between items
            check_res = await db.execute(select(RecoveryJob.status).where(RecoveryJob.id == job.id))
            current_status = check_res.scalar()
            if current_status == RecoveryJobStatus.CANCELLED.value:
                logger.warning(f"RecoveryJob {job.id} was cancelled by operator.")
                item.status = RecoveryItemStatus.CANCELLED.value
                await db.commit()
                break

            if item.status == RecoveryItemStatus.COMPLETED.value:
                continue

            item.status = RecoveryItemStatus.IN_PROGRESS.value
            await db.commit()

            try:
                item.status = RecoveryItemStatus.VERIFYING.value
                await db.commit()

                # 2. Decrypt, Decompress & Verify SHA-256
                plaintext = await self.get_verified_item_payload(db=db, job=job, item=item)

                # 3. Check Overwrite Conflict
                should_write, final_target_path = path_validator.resolve_file_conflict(
                    target_path=item.target_path,
                    overwrite_policy=job.overwrite_policy,
                )

                if not should_write:
                    item.status = RecoveryItemStatus.SKIPPED.value
                    item.error_message = "File skipped: Target already exists on disk (policy=SKIP)."
                    job.files_skipped += 1
                else:
                    # 4. Write to staging directory first
                    staging_path = path_validator.create_staging_path(job.id, item.file_version_id)
                    with open(staging_path, "wb") as sf:
                        sf.write(plaintext)

                    # 5. Atomic placement to verified destination
                    path_validator.commit_staged_file(staging_path, final_target_path)

                    item.status = RecoveryItemStatus.COMPLETED.value
                    item.target_path = final_target_path
                    item.sha256_verified = True
                    item.bytes_restored = len(plaintext)

                    job.files_restored += 1
                    job.bytes_restored += len(plaintext)

            except Exception as e:
                logger.exception(f"Recovery Failed for item {item.id} (file: '{item.original_path}'): {str(e)}")
                item.status = RecoveryItemStatus.FAILED.value
                item.error_message = str(e)[:1024]
                job.files_failed += 1

            try:
                await db.commit()
            except Exception as commit_err:
                # The session is unusable after a failed flush: roll back, then record the
                # failure with set-based updates so the job can never remain IN_PROGRESS.
                logger.exception(f"Recovery commit failed for job {job_id}: {commit_err}")
                failed_item_id = item.id
                await db.rollback()
                await db.execute(
                    update(RecoveryJobItem)
                    .where(RecoveryJobItem.id == failed_item_id)
                    .values(
                        status=RecoveryItemStatus.FAILED.value,
                        error_message=f"Database commit failed: {str(commit_err)[:900]}",
                    )
                )
                await db.execute(
                    update(RecoveryJob)
                    .where(RecoveryJob.id == job_id)
                    .values(
                        status=RecoveryJobStatus.FAILED.value,
                        error_message="Database commit failed during restoration; remaining files were not restored.",
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()
                path_validator.cleanup_staging_dir(job_id)
                reloaded = await db.execute(
                    select(RecoveryJob)
                    .where(RecoveryJob.id == job_id)
                    .options(selectinload(RecoveryJob.items))
                    .execution_options(populate_existing=True)
                )
                return reloaded.scalar_one()

        # Clean staging dir
        path_validator.cleanup_staging_dir(job.id)

        # Final Job Status Calculation
        job.completed_at = datetime.now(timezone.utc)
        if job.status != RecoveryJobStatus.CANCELLED.value:
            if job.files_failed == 0 and job.files_restored > 0:
                # All attempted files restored (some may also be skipped)
                job.status = RecoveryJobStatus.COMPLETED.value
            elif job.files_restored > 0 and job.files_failed > 0:
                # Partial success: some restored, some failed
                job.status = RecoveryJobStatus.PARTIAL.value
            elif job.files_failed == 0 and job.files_skipped > 0:
                # All files were skipped (SKIP policy, file already exists) — this is not an error
                job.status = RecoveryJobStatus.COMPLETED.value
            elif job.files_failed == 0 and job.files_restored == 0 and job.files_skipped == 0:
                # No items processed at all (empty job or already completed items)
                job.status = RecoveryJobStatus.COMPLETED.value
            else:
                job.status = RecoveryJobStatus.FAILED.value
                if not job.error_message and job.items:
                    failed_items = [it for it in job.items if it.status == RecoveryItemStatus.FAILED.value]
                    if failed_items and failed_items[0].error_message:
                        job.error_message = failed_items[0].error_message

        # Final Audit Log
        db.add(AuditLog(
            organization_id=job.organization_id,
            user_id=job.requested_by_id,
            action=f"RECOVERY_JOB_{job.status}",
            resource_type="RecoveryJob",
            resource_id=str(job.id),
            details={
                "job_id": str(job.id),
                "status": job.status,
                "error_message": job.error_message,
                "files_restored": job.files_restored,
                "files_failed": job.files_failed,
                "files_skipped": job.files_skipped,
                "bytes_restored": job.bytes_restored,
            },
        ))
        await db.commit()
        await db.refresh(job)

        # Broadcast live status update to operator WebSockets
        try:
            await alert_service.broadcast({
                "type": "RECOVERY_JOB_UPDATED",
                "job_id": str(job.id),
                "status": job.status,
                "files_restored": job.files_restored,
                "files_failed": job.files_failed,
                "total_files": job.total_files,
            })
        except Exception:
            pass

        return job

    async def cancel_recovery_job(
        self,
        db: AsyncSession,
        organization_id: Optional[uuid.UUID],
        user_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> RecoveryJob:
        """Cancels a pending or running recovery job."""
        stmt = select(RecoveryJob).where(
            RecoveryJob.id == job_id,
            RecoveryJob.requested_by_id == user_id,
        )
        owned_file_ids = (
            select(File.id)
            .join(Device, File.device_id == Device.id)
            .where(
                Device.user_id == user_id,
                Device.organization_id == organization_id,
            )
        )
        stmt = stmt.where(
            RecoveryJob.items.any(RecoveryJobItem.file_id.in_(owned_file_ids)),
            ~RecoveryJob.items.any(~RecoveryJobItem.file_id.in_(owned_file_ids)),
        )
        if organization_id is not None:
            stmt = stmt.where(RecoveryJob.organization_id == organization_id)
        else:
            stmt = stmt.where(RecoveryJob.organization_id.is_(None))
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            raise ValueError("Recovery job not found.")

        if job.status in (RecoveryJobStatus.COMPLETED.value, RecoveryJobStatus.FAILED.value):
            raise ValueError(f"Cannot cancel a job that is already {job.status}.")

        job.status = RecoveryJobStatus.CANCELLED.value
        path_validator.cleanup_staging_dir(job.id)

        # Mark pending items as cancelled
        await db.execute(
            update(RecoveryJobItem)
            .where(
                RecoveryJobItem.recovery_job_id == job.id,
                RecoveryJobItem.status.in_([RecoveryItemStatus.PENDING.value, RecoveryItemStatus.IN_PROGRESS.value]),
            )
            .values(status=RecoveryItemStatus.CANCELLED.value)
        )

        db.add(AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action="RECOVERY_JOB_CANCELLED",
            resource_type="RecoveryJob",
            resource_id=str(job.id),
            details={"job_id": str(job.id)},
        ))
        await db.commit()
        await db.refresh(job)
        return job

    async def retry_recovery_job(
        self,
        db: AsyncSession,
        organization_id: Optional[uuid.UUID],
        user_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> RecoveryJob:
        """Resets failed or cancelled items to PENDING and restarts execution."""
        stmt = (
            select(RecoveryJob)
            .where(
                RecoveryJob.id == job_id,
                RecoveryJob.requested_by_id == user_id,
            )
            .options(selectinload(RecoveryJob.items))
        )
        owned_file_ids = (
            select(File.id)
            .join(Device, File.device_id == Device.id)
            .where(
                Device.user_id == user_id,
                Device.organization_id == organization_id,
            )
        )
        stmt = stmt.where(
            RecoveryJob.items.any(RecoveryJobItem.file_id.in_(owned_file_ids)),
            ~RecoveryJob.items.any(~RecoveryJobItem.file_id.in_(owned_file_ids)),
        )
        if organization_id is not None:
            stmt = stmt.where(RecoveryJob.organization_id == organization_id)
        else:
            stmt = stmt.where(RecoveryJob.organization_id.is_(None))
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            raise ValueError("Recovery job not found.")

        failed_items = [item for item in job.items if item.status in (RecoveryItemStatus.FAILED.value, RecoveryItemStatus.CANCELLED.value)]
        if not failed_items:
            raise ValueError("No failed or cancelled items eligible for retry.")

        for item in failed_items:
            item.status = RecoveryItemStatus.PENDING.value
            item.error_message = None

        job.files_failed = 0
        job.status = RecoveryJobStatus.PENDING.value

        db.add(AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action="RECOVERY_JOB_RETRIED",
            resource_type="RecoveryJob",
            resource_id=str(job.id),
            details={"job_id": str(job.id), "retried_items": len(failed_items)},
        ))
        await db.commit()

        # Re-execute job
        return await self.execute_recovery_job(db=db, job_id=job.id)


recovery_service = RecoveryService()

