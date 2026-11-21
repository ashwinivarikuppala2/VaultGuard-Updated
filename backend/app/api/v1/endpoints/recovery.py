import asyncio
import logging
import os
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse
from urllib.parse import quote

from app.core.responses import ApiResponse, success_response
from app.database.session import AsyncSessionLocal, get_db
from app.models.audit_log import AuditLog
from app.models.device import Device
from app.models.future_placeholders import File, FileVersion
from app.models.role import Role
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
from app.models.role import RoleType
from app.models.threat import Detection
from app.models.user import User
from app.schemas.recovery import (
    ApprovalActionRequest,
    CreateBulkRestoreRequest,
    CreateFolderRestoreRequest,
    CreatePointInTimeRestoreRequest,
    CreateSingleRestoreRequest,
    RecoveryJobListResponse,
    RecoveryJobResponse,
    RecoveryPointOption,
    RestorePreviewRequest,
    RestorePreviewResponse,
)
from app.repositories.device_repository import DeviceRepository
from app.security.rbac import get_current_user, require_roles
from app.services.recovery.integrity_service import IntegrityVerificationError
from app.services.recovery.path_validator import PathValidationError
from app.services.recovery.recovery_service import recovery_service
from app.services.recovery.risk_assessor import risk_assessor

logger = logging.getLogger("vaultguard.api.recovery")

router = APIRouter()


async def _run_recovery_job_background(job_id: uuid.UUID) -> None:
    """Independent background runner using isolated database session."""
    async with AsyncSessionLocal() as session:
        try:
            await recovery_service.execute_recovery_job(db=session, job_id=job_id)
        except Exception as e:
            logger.error(f"Background recovery job {job_id} encountered unexpected error: {str(e)}", exc_info=True)


async def _resolve_recovery_scope(
    db: AsyncSession,
    current_user: User,
    for_restore: bool = False,
):
    """Resolve visible or restorable file scope for the authenticated role."""
    if current_user.role.name in [RoleType.INDIVIDUAL.value, RoleType.EMPLOYEE.value]:
        device_ids = await DeviceRepository(db).list_ids_by_user(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
        return current_user.organization_id, device_ids
    if current_user.role.name == RoleType.ADMIN.value:
        if for_restore or not current_user.organization_id:
            device_ids = await DeviceRepository(db).list_ids_by_user(
                user_id=current_user.id,
                organization_id=current_user.organization_id,
            )
            return current_user.organization_id, device_ids
        device_repository = DeviceRepository(db)
        own_device_ids = await device_repository.list_ids_by_user(
            current_user.id, current_user.organization_id
        )
        employee_device_ids = await device_repository.list_employee_ids_by_organization(
            current_user.organization_id
        )
        return current_user.organization_id, list(dict.fromkeys([*own_device_ids, *employee_device_ids]))
    return None, []


def _visible_recovery_file_ids(current_user: User):
    visible_device_ids = select(Device.id).where(
        Device.user_id == current_user.id,
        Device.organization_id == current_user.organization_id,
    )
    if current_user.role.name == RoleType.ADMIN.value and current_user.organization_id:
        employee_user_ids = (
            select(User.id)
            .join(Role, User.role_id == Role.id)
            .where(
                User.organization_id == current_user.organization_id,
                Role.name == RoleType.EMPLOYEE.value,
            )
        )
        visible_device_ids = select(Device.id).where(
            Device.organization_id == current_user.organization_id,
            or_(
                Device.user_id == current_user.id,
                Device.user_id.in_(employee_user_ids),
            ),
        )
    return select(File.id).where(File.device_id.in_(visible_device_ids))


def _admin_recovery_job_filter(current_user: User):
    """Admin job history is limited to the admin's own jobs and employee-owned files."""
    visible_file_ids = _visible_recovery_file_ids(current_user)
    return and_(
        RecoveryJob.organization_id == current_user.organization_id
        if current_user.organization_id is not None
        else RecoveryJob.organization_id.is_(None),
        or_(
            RecoveryJob.requested_by_id == current_user.id,
            RecoveryJob.items.any(RecoveryJobItem.file_id.in_(visible_file_ids)),
        ),
        ~RecoveryJob.items.any(~RecoveryJobItem.file_id.in_(visible_file_ids)),
    )


def _employee_recovery_job_filter(current_user: User):
    visible_file_ids = _visible_recovery_file_ids(current_user)
    return and_(
        RecoveryJob.organization_id == current_user.organization_id
        if current_user.organization_id is not None
        else RecoveryJob.organization_id.is_(None),
        RecoveryJob.requested_by_id == current_user.id,
        ~RecoveryJob.items.any(~RecoveryJobItem.file_id.in_(visible_file_ids)),
    )


# ==================== 1. Restore Preview ====================

@router.post(
    "/preview",
    response_model=ApiResponse[RestorePreviewResponse],
    summary="Preview recovery job, detect path collisions, and assess Module 3 threat risk",
)
async def preview_restore_endpoint(
    payload: RestorePreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id, device_ids = await _resolve_recovery_scope(db, current_user, for_restore=True)

    try:
        preview_data = await recovery_service.preview_restore(
            db=db,
            organization_id=org_id,
            job_type=payload.job_type,
            file_version_ids=payload.file_version_ids,
            folder_path=payload.folder_path,
            device_id=payload.device_id,
            device_ids=device_ids,
            point_in_time=payload.point_in_time,
            destination_path=payload.destination_path,
            destination_type=payload.destination_type,
            overwrite_policy=payload.overwrite_policy,
        )
        return success_response(
            data=RestorePreviewResponse(**preview_data),
            message="Restoration preview generated successfully.",
        )
    except (ValueError, PathValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 2. Single-File Restore ====================

@router.post(
    "/restore/single",
    response_model=ApiResponse[RecoveryJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Initiate single-file restoration from an immutable historical snapshot",
)
async def restore_single_file(
    payload: CreateSingleRestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id, device_ids = await _resolve_recovery_scope(db, current_user, for_restore=True)

    try:
        job = await recovery_service.create_recovery_job(
            db=db,
            organization_id=org_id,
            requested_by_id=current_user.id,
            job_type=RecoveryJobType.SINGLE_FILE.value,
            file_version_ids=[payload.file_version_id],
            device_ids=device_ids,
            destination_path=payload.destination_path,
            destination_type=payload.destination_type,
            overwrite_policy=payload.overwrite_policy,
        )

        if not job.requires_approval:
            job = await recovery_service.execute_recovery_job(db=db, job_id=job.id)
            if job.status == RecoveryJobStatus.FAILED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=job.error_message or "Single-file restoration failed.",
                )

        return success_response(
            data=RecoveryJobResponse.model_validate(job),
            message="Single-file restoration completed successfully.",
        )
    except (ValueError, PathValidationError, IntegrityVerificationError, PermissionError, OSError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 3. Folder Restore ====================

@router.post(
    "/restore/folder",
    response_model=ApiResponse[RecoveryJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Initiate folder hierarchy restoration",
)
async def restore_folder(
    payload: CreateFolderRestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id, device_ids = await _resolve_recovery_scope(db, current_user, for_restore=True)

    try:
        job = await recovery_service.create_recovery_job(
            db=db,
            organization_id=org_id,
            requested_by_id=current_user.id,
            job_type=RecoveryJobType.FOLDER.value,
            folder_path=payload.folder_path,
            device_id=payload.device_id,
            device_ids=device_ids,
            destination_path=payload.destination_path,
            destination_type=payload.destination_type,
            overwrite_policy=payload.overwrite_policy,
        )

        if not job.requires_approval:
            job = await recovery_service.execute_recovery_job(db=db, job_id=job.id)
            if job.status == RecoveryJobStatus.FAILED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=job.error_message or "Folder restoration failed.",
                )

        return success_response(
            data=RecoveryJobResponse.model_validate(job),
            message=f"Folder restoration completed ({job.total_files} files).",
        )
    except (ValueError, PathValidationError, IntegrityVerificationError, PermissionError, OSError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 4. Bulk Restore ====================

@router.post(
    "/restore/bulk",
    response_model=ApiResponse[RecoveryJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Initiate multi-file bulk restoration with safety limits",
)
async def restore_bulk(
    payload: CreateBulkRestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN, RoleType.EMPLOYEE, RoleType.INDIVIDUAL])),
):
    org_id, device_ids = await _resolve_recovery_scope(db, current_user, for_restore=True)

    if len(payload.file_version_ids) > 1000:
        raise HTTPException(status_code=400, detail="Bulk restore limit exceeded: Maximum 1000 items per job.")

    try:
        job = await recovery_service.create_recovery_job(
            db=db,
            organization_id=org_id,
            requested_by_id=current_user.id,
            job_type=RecoveryJobType.BULK.value,
            file_version_ids=payload.file_version_ids,
            device_ids=device_ids,
            destination_path=payload.destination_path,
            destination_type=payload.destination_type,
            overwrite_policy=payload.overwrite_policy,
        )

        if not job.requires_approval:
            job = await recovery_service.execute_recovery_job(db=db, job_id=job.id)
            if job.status == RecoveryJobStatus.FAILED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=job.error_message or "Bulk restoration failed.",
                )

        return success_response(
            data=RecoveryJobResponse.model_validate(job),
            message=f"Bulk restoration completed ({job.total_files} items).",
        )
    except (ValueError, PathValidationError, IntegrityVerificationError, PermissionError, OSError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 5. Point-in-Time Restore ====================

@router.post(
    "/restore/point-in-time",
    response_model=ApiResponse[RecoveryJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Restore endpoint or org files to the state as of a target timestamp",
)
async def restore_point_in_time(
    payload: CreatePointInTimeRestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN, RoleType.EMPLOYEE, RoleType.INDIVIDUAL])),
):
    org_id, device_ids = await _resolve_recovery_scope(db, current_user, for_restore=True)

    try:
        job = await recovery_service.create_recovery_job(
            db=db,
            organization_id=org_id,
            requested_by_id=current_user.id,
            job_type=RecoveryJobType.POINT_IN_TIME.value,
            device_id=payload.device_id,
            device_ids=device_ids,
            snapshot_time=payload.snapshot_time,
            destination_path=payload.destination_path,
            destination_type=payload.destination_type,
            overwrite_policy=payload.overwrite_policy,
        )

        if not job.requires_approval:
            job = await recovery_service.execute_recovery_job(db=db, job_id=job.id)
            if job.status == RecoveryJobStatus.FAILED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=job.error_message or "Point-in-time restoration failed.",
                )

        return success_response(
            data=RecoveryJobResponse.model_validate(job),
            message=f"Point-in-time recovery completed ({job.total_files} items).",
        )
    except (ValueError, PathValidationError, IntegrityVerificationError, PermissionError, OSError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 6. List Recovery Jobs ====================

@router.get(
    "/jobs",
    response_model=ApiResponse[RecoveryJobListResponse],
    summary="List recovery jobs with status filters and pagination",
)
async def list_recovery_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    job_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(RecoveryJob)
    if current_user.role.name == RoleType.ADMIN.value:
        query = query.where(_admin_recovery_job_filter(current_user))
    else:
        query = query.where(_employee_recovery_job_filter(current_user))

    if status_filter:
        query = query.where(RecoveryJob.status == status_filter.upper())
    if job_type:
        query = query.where(RecoveryJob.job_type == job_type.upper())

    total_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(total_query)
    total = total_res.scalar_one()

    query = query.order_by(desc(RecoveryJob.created_at)).offset((page - 1) * page_size).limit(page_size)
    res = await db.execute(query)
    jobs = res.scalars().all()

    return success_response(
        data=RecoveryJobListResponse(
            items=[RecoveryJobResponse.model_validate(j) for j in jobs],
            total=total,
            page=page,
            page_size=page_size,
        ),
        message="Recovery jobs retrieved.",
    )


# ==================== 7. Get Recovery Job Details ====================

@router.get(
    "/jobs/{job_id}",
    response_model=ApiResponse[RecoveryJobResponse],
    summary="Get recovery job details with full per-item results",
)
async def get_recovery_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(RecoveryJob).where(RecoveryJob.id == job_id).options(selectinload(RecoveryJob.items))
    if current_user.role.name == RoleType.ADMIN.value:
        q = q.where(_admin_recovery_job_filter(current_user))
    else:
        q = q.where(_employee_recovery_job_filter(current_user))

    res = await db.execute(q)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Recovery job not found.")

    return success_response(
        data=RecoveryJobResponse.model_validate(job),
        message="Recovery job retrieved.",
    )


async def _get_accessible_completed_job(
    job_id: uuid.UUID,
    db: AsyncSession,
    current_user: User,
) -> RecoveryJob:
    query = (
        select(RecoveryJob)
        .where(RecoveryJob.id == job_id)
        .options(selectinload(RecoveryJob.items))
    )
    if current_user.role.name == RoleType.ADMIN.value:
        query = query.where(_admin_recovery_job_filter(current_user))
    else:
        query = query.where(_employee_recovery_job_filter(current_user))

    result = await db.execute(query)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Recovery job not found.")
    if job.status not in (RecoveryJobStatus.COMPLETED.value, RecoveryJobStatus.PARTIAL.value):
        raise HTTPException(status_code=409, detail="Recovery job has not completed.")
    return job


@router.get(
    "/jobs/{job_id}/items/{item_id}/download",
    summary="Download an integrity-verified file from a completed recovery job",
)
async def download_restored_item(
    job_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_accessible_completed_job(job_id, db, current_user)
    item = next((entry for entry in job.items if entry.id == item_id), None)
    if not item or item.status != RecoveryItemStatus.COMPLETED.value or not item.sha256_verified:
        raise HTTPException(status_code=404, detail="Verified restored file not found.")

    try:
        payload = await recovery_service.get_verified_item_payload(db=db, job=job, item=item)
    except (ValueError, IntegrityVerificationError) as error:
        raise HTTPException(status_code=400, detail=str(error))

    filename = os.path.basename(item.original_path.replace("\\", "/")) or "restored-file"
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(
    "/jobs/{job_id}/download",
    summary="Download verified files from a completed recovery job as a ZIP archive",
)
async def download_recovery_archive(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_accessible_completed_job(job_id, db, current_user)
    items = [
        item for item in job.items
        if item.status == RecoveryItemStatus.COMPLETED.value and item.sha256_verified
    ]
    if not items:
        raise HTTPException(status_code=404, detail="No verified restored files are available.")

    archive = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for item in items:
            path = item.original_path.replace("\\", "/")
            if len(path) >= 2 and path[1] == ":":
                path = path[2:]
            path = path.lstrip("/")
            parts = [part for part in path.split("/") if part and part != "."]
            if not parts or ".." in parts:
                raise HTTPException(status_code=400, detail="Unsafe restored file path in recovery job.")
            payload = await recovery_service.get_verified_item_payload(db=db, job=job, item=item)
            zip_file.writestr("/".join(parts), payload)

    archive.seek(0)

    def stream_archive():
        while chunk := archive.read(1024 * 1024):
            yield chunk

    return StreamingResponse(
        stream_archive(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="vaultguard-recovery-{job.id}.zip"'},
        background=BackgroundTask(archive.close),
    )


# ==================== 8. Cancel Job ====================

@router.post(
    "/jobs/{job_id}/cancel",
    response_model=ApiResponse[RecoveryJobResponse],
    summary="Cancel a pending or running recovery job",
)
async def cancel_job_endpoint(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN, RoleType.EMPLOYEE, RoleType.INDIVIDUAL])),
):
    org_id, device_ids = await _resolve_recovery_scope(db, current_user)

    try:
        job = await recovery_service.cancel_recovery_job(
            db=db,
            organization_id=org_id,
            user_id=current_user.id,
            job_id=job_id,
        )
        return success_response(
            data=RecoveryJobResponse.model_validate(job),
            message="Recovery job cancelled.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 9. Retry Failed Job Items ====================

@router.post(
    "/jobs/{job_id}/retry",
    response_model=ApiResponse[RecoveryJobResponse],
    summary="Retry failed or cancelled items in a recovery job without duplicating completed work",
)
async def retry_job_endpoint(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN, RoleType.EMPLOYEE, RoleType.INDIVIDUAL])),
):
    org_id, device_ids = await _resolve_recovery_scope(db, current_user)

    try:
        job = await recovery_service.retry_recovery_job(
            db=db,
            organization_id=org_id,
            user_id=current_user.id,
            job_id=job_id,
        )
        return success_response(
            data=RecoveryJobResponse.model_validate(job),
            message="Recovery job retried.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 10. Recommended Recovery Points ====================

@router.get(
    "/recovery-points",
    response_model=ApiResponse[List[RecoveryPointOption]],
    summary="Suggest candidate recovery points with Module 3 threat risk labels",
)
async def get_recovery_points(
    device_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id, device_ids = await _resolve_recovery_scope(db, current_user)

    # Find distinct snapshot timestamps from file versions
    query = (
        select(FileVersion.created_at, func.count(FileVersion.id))
        .join(File)
    )
    if current_user.role.name == RoleType.ADMIN.value and org_id:
        my_ids = await DeviceRepository(db).list_ids_by_user(
            current_user.id, current_user.organization_id
        )
        employee_ids = await DeviceRepository(db).list_employee_ids_by_organization(org_id)
        device_ids = list(dict.fromkeys([*my_ids, *employee_ids]))

    if device_ids is not None:
        query = query.where(File.device_id.in_(device_ids))
    elif org_id is not None:
        query = query.where(File.organization_id == org_id)

    if device_id:
        query = query.where(File.device_id == device_id)

    query = query.group_by(FileVersion.created_at).order_by(desc(FileVersion.created_at)).limit(15)
    res = await db.execute(query)
    snapshots = res.all()

    # Query earliest threat detection on this device/org
    det_query = select(Detection)
    if device_ids is not None:
        det_query = det_query.where(Detection.device_id.in_(device_ids))
    elif org_id is not None:
        det_query = det_query.where(Detection.organization_id == org_id)
    det_query = det_query.order_by(Detection.created_at.asc())
    det_res = await db.execute(det_query)
    earliest_det = det_res.scalars().first()

    points: List[RecoveryPointOption] = []
    for snapshot_time, count in snapshots:
        if earliest_det and snapshot_time >= earliest_det.created_at:
            label = ThreatRiskLabel.POTENTIALLY_SUSPICIOUS.value
            summary = f"Created after threat detection '{earliest_det.threat_name}' at {earliest_det.created_at.strftime('%Y-%m-%d %H:%M')}"
        elif earliest_det and snapshot_time < earliest_det.created_at:
            label = ThreatRiskLabel.NO_KNOWN_THREAT.value
            summary = f"Pre-incident snapshot. Created before earliest detection at {earliest_det.created_at.strftime('%Y-%m-%d %H:%M')}"
        else:
            label = ThreatRiskLabel.NO_KNOWN_THREAT.value
            summary = "No recorded security incidents on endpoint. Note: Heuristics do not guarantee absence of zero-days."

        points.append(RecoveryPointOption(
            snapshot_time=snapshot_time,
            total_files=count,
            risk_label=label,
            threat_summary=summary,
        ))

    return success_response(
        data=points,
        message="Candidate recovery points retrieved.",
    )


# ==================== 11. Dual-Custody Approval ====================

@router.post(
    "/approvals/{approval_id}/action",
    response_model=ApiResponse[Dict[str, Any]],
    summary="Approve or reject a dual-custody recovery authorization request",
)
async def approve_recovery_request(
    approval_id: uuid.UUID,
    payload: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN])),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User must belong to an organization.")

    app_res = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.organization_id == current_user.organization_id,
        )
    )
    approval = app_res.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    if approval.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Request is already {approval.status}.")

    # Separation of duties: Requester cannot approve their own request
    if approval.requested_by_id == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Dual-custody security policy violation: Requester cannot approve their own recovery request.",
        )

    action_upper = payload.action.upper()
    if action_upper not in ("APPROVE", "REJECT"):
        raise HTTPException(status_code=400, detail="Action must be APPROVE or REJECT.")

    # If approved, find associated RecoveryJob and kick off execution
    job_res = await db.execute(
        select(RecoveryJob)
        .where(RecoveryJob.approval_request_id == approval.id)
        .options(selectinload(RecoveryJob.items))
    )
    job = job_res.scalar_one_or_none()
    if not job or not job.items:
        raise HTTPException(status_code=404, detail="Recovery job not found.")

    requester_res = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .where(User.id == job.requested_by_id)
    )
    requester = requester_res.scalar_one_or_none()
    if (
        not requester
        or requester.role.name != RoleType.ADMIN.value
        or approval.requested_by_id != job.requested_by_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Admins may only approve or reject recovery jobs initiated for Admin-owned files.",
        )

    file_ids = list({item.file_id for item in job.items})
    owned_files_res = await db.execute(
        select(File.id)
        .join(Device, File.device_id == Device.id)
        .where(
            File.id.in_(file_ids),
            Device.user_id == job.requested_by_id,
            Device.organization_id == current_user.organization_id,
        )
    )
    if len(owned_files_res.scalars().all()) != len(file_ids):
        raise HTTPException(
            status_code=403,
            detail="Admins may only approve or reject recovery jobs for files owned by the requester.",
        )

    approval.status = "APPROVED" if action_upper == "APPROVE" else "REJECTED"
    approval.approved_by_id = current_user.id

    if job and action_upper == "REJECT":
        job.status = RecoveryJobStatus.CANCELLED.value
        job.error_message = f"Recovery request rejected by {current_user.full_name}: {payload.notes or 'No reason provided.'}"

    # Immutable Audit Log
    db.add(AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action=f"RECOVERY_APPROVAL_{action_upper}",
        resource_type="ApprovalRequest",
        resource_id=str(approval.id),
        details={
            "approval_id": str(approval.id),
            "action": action_upper,
            "job_id": str(job.id) if job else None,
            "notes": payload.notes,
        },
    ))
    await db.commit()

    # Schedule execution only after the APPROVED status is durable, so the background
    # runner cannot observe the approval as still PENDING.
    if job and action_upper == "APPROVE":
        asyncio.create_task(_run_recovery_job_background(job.id))

    return success_response(
        data={"approval_id": str(approval.id), "status": approval.status, "action": action_upper},
        message=f"Recovery request {action_upper}D successfully.",
    )

