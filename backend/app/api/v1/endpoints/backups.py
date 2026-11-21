import base64
import binascii
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.config import settings
from app.core.exceptions import FileSizeLimitException, MalwareDetectedException
from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.user import User
from app.schemas.backup import (
    BackupJobResponse,
    BackupSnapshotResponse,
    EmployeeBackupDetails,
    EmployeeBackupSummary,
    FileHistoryItem,
    FileVersionResponse,
    ManualBackupRequest,
    StartBackupRequest,
)
from app.schemas.common import PaginatedResponse
from app.security.rbac import get_current_user
from app.services.backup_service import BackupService

router = APIRouter()

# Maximum upload size in bytes, driven by settings.MAX_UPLOAD_SIZE_MB.
# This is enforced server-side independently of nginx so the backend
# returns a structured JSON 413 instead of nginx's plain-text 413.
_MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/start", response_model=ApiResponse[BackupJobResponse], status_code=status.HTTP_201_CREATED)
async def start_backup(
    request: Request,
    request_in: StartBackupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[BackupJobResponse]:
    """Start or queue a backup job for a device."""
    service = BackupService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    job = await service.start_backup_job(
        request_in=request_in,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=job.model_dump(), trace_id=trace_id)


@router.post("/manual", response_model=ApiResponse[FileVersionResponse], status_code=status.HTTP_201_CREATED)
async def manual_backup(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FileVersionResponse]:
    """
    Manually upload and encrypt a single file version immediately.

    Accepts multipart/form-data for raw browser uploads and retains support for
    legacy base64 JSON clients. Multipart avoids the ~33% base64 size inflation.

    The file is read into memory once, then:
      1. Size-checked against MAX_UPLOAD_SIZE_MB.
      2. Scanned by ClamAV (mandatory — backup is blocked if scan fails).
      3. Compressed + AES-256-GCM encrypted.
      4. Written to MinIO permanent storage.
      5. Metadata committed to the database.
    """
    service = BackupService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    content_type = request.headers.get("content-type", "").lower()
    protected_folder_id: Optional[uuid.UUID]
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        try:
            device_id = uuid.UUID(str(form.get("device_id", "")))
            file_path = str(form.get("file_path", ""))
            protected_folder_value = form.get("protected_folder_id")
            protected_folder_id = (
                uuid.UUID(str(protected_folder_value))
                if protected_folder_value
                else None
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid device or protected-folder identifier.") from exc

        uploaded_file = form.get("file")
        if not isinstance(uploaded_file, StarletteUploadFile):
            raise HTTPException(status_code=422, detail="A file upload is required.")
        if not file_path or len(file_path) > 1024:
            raise HTTPException(status_code=422, detail="file_path must contain 1 to 1024 characters.")
        # Starlette spools large uploads to disk, avoiding base64 payload inflation.
        raw_bytes = await uploaded_file.read()
    elif content_type.startswith("application/json"):
        try:
            manual_request = ManualBackupRequest.model_validate(await request.json())
            device_id = manual_request.device_id
            file_path = manual_request.file_path
            protected_folder_id = manual_request.protected_folder_id
            raw_bytes = base64.b64decode(
                manual_request.file_content_base64,
                validate=True,
            )
        except (binascii.Error, ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail="Invalid JSON or base64 manual-backup payload.") from exc
    else:
        raise HTTPException(status_code=415, detail="Use multipart/form-data or application/json.")

    # Enforce server-side size limit — returns a structured JSON 413 error
    # rather than nginx's plain-text "Request Entity Too Large".
    if len(raw_bytes) > _MAX_UPLOAD_BYTES:
        raise FileSizeLimitException(
            file_size_bytes=len(raw_bytes),
            max_size_bytes=_MAX_UPLOAD_BYTES,
        )

    try:
        version = await service.manual_backup_bytes(
            device_id=device_id,
            file_path=file_path,
            raw_bytes=raw_bytes,
            protected_folder_id=protected_folder_id,
            current_user=current_user,
            ip_address=client_ip,
            user_agent=user_agent,
        )
    except MalwareDetectedException as exc:
        # Scanner failures are service errors, not malware detections.
        return JSONResponse(
            status_code=422 if exc.code == "MALWARE_DETECTED" else 503,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )
    except FileSizeLimitException as exc:
        return JSONResponse(
            status_code=413,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=version.model_dump(), trace_id=trace_id)


@router.get(
    "/employees",
    response_model=ApiResponse[list[EmployeeBackupSummary]],
)
async def list_employee_backups(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[EmployeeBackupSummary]]:
    """List organization employees with backup usage summaries (Admin read-only)."""
    service = BackupService(db)
    employees = await service.list_employee_backup_summaries(current_user)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(
        data=[employee.model_dump() for employee in employees],
        trace_id=trace_id,
    )


@router.get(
    "/employees/{employee_id}",
    response_model=ApiResponse[EmployeeBackupDetails],
)
async def get_employee_backup_details(
    request: Request,
    employee_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    recovery_skip: int = Query(0, ge=0),
    recovery_limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[EmployeeBackupDetails]:
    """View one organization employee's backup and recovery metadata read-only."""
    service = BackupService(db)
    details = await service.get_employee_backup_details(
        employee_id=employee_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
        recovery_skip=recovery_skip,
        recovery_limit=recovery_limit,
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=details.model_dump(), trace_id=trace_id)


@router.get("", response_model=ApiResponse[PaginatedResponse[BackupSnapshotResponse]])
async def list_backups(
    request: Request,
    device_id: Optional[uuid.UUID] = None,
    owner_scope: Optional[Literal["mine", "employees"]] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[BackupSnapshotResponse]]:
    """List recent backup version snapshots across protected files."""
    service = BackupService(db)
    items, total = await service.list_snapshots(
        current_user=current_user,
        device_id=device_id,
        owner_scope=owner_scope,
        skip=skip,
        limit=limit,
    )
    trace_id = getattr(request.state, "trace_id", None)
    data = PaginatedResponse[BackupSnapshotResponse](
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )
    return success_response(data=data.model_dump(), trace_id=trace_id)


@router.get("/jobs", response_model=ApiResponse[PaginatedResponse[BackupJobResponse]])
async def list_backup_jobs(
    request: Request,
    device_id: Optional[uuid.UUID] = None,
    owner_scope: Optional[Literal["mine", "employees"]] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[BackupJobResponse]]:
    """List backup job execution runs and their progress telemetry."""
    service = BackupService(db)
    items, total = await service.list_jobs(
        current_user=current_user,
        device_id=device_id,
        owner_scope=owner_scope,
        status=status,
        skip=skip,
        limit=limit,
    )
    trace_id = getattr(request.state, "trace_id", None)
    data = PaginatedResponse[BackupJobResponse](
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )
    return success_response(data=data.model_dump(), trace_id=trace_id)


@router.get("/history/{file_id}", response_model=ApiResponse[FileHistoryItem])
async def get_file_history(
    request: Request,
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[FileHistoryItem]:
    """Retrieve full version history timeline for a specific protected file."""
    service = BackupService(db)
    history = await service.get_file_history(file_id=file_id, current_user=current_user)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=history.model_dump(), trace_id=trace_id)
