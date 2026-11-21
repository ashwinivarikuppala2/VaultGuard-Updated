import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import inspect as sa_inspect

from app.models.recovery import DestinationType, OverwritePolicy, RecoveryJobType


# ==================== Request Schemas ====================

class RestorePreviewRequest(BaseModel):
    job_type: str = Field(..., description="SINGLE_FILE, FOLDER, BULK, or POINT_IN_TIME")
    file_version_ids: Optional[List[uuid.UUID]] = None
    folder_path: Optional[str] = None
    device_id: Optional[uuid.UUID] = None
    point_in_time: Optional[datetime] = None
    destination_path: Optional[str] = None
    destination_type: str = Field(default=DestinationType.SAFE_DIR.value)
    overwrite_policy: str = Field(default=OverwritePolicy.SKIP.value)


class CreateSingleRestoreRequest(BaseModel):
    file_version_id: uuid.UUID
    destination_path: Optional[str] = None
    destination_type: str = Field(default=DestinationType.SAFE_DIR.value)
    overwrite_policy: str = Field(default=OverwritePolicy.SKIP.value)


class CreateFolderRestoreRequest(BaseModel):
    folder_path: str
    device_id: Optional[uuid.UUID] = None
    destination_path: Optional[str] = None
    destination_type: str = Field(default=DestinationType.SAFE_DIR.value)
    overwrite_policy: str = Field(default=OverwritePolicy.SKIP.value)


class CreateBulkRestoreRequest(BaseModel):
    file_version_ids: List[uuid.UUID]
    destination_path: Optional[str] = None
    destination_type: str = Field(default=DestinationType.SAFE_DIR.value)
    overwrite_policy: str = Field(default=OverwritePolicy.SKIP.value)


class CreatePointInTimeRestoreRequest(BaseModel):
    snapshot_time: datetime
    device_id: Optional[uuid.UUID] = None
    destination_path: Optional[str] = None
    destination_type: str = Field(default=DestinationType.SAFE_DIR.value)
    overwrite_policy: str = Field(default=OverwritePolicy.SKIP.value)


class ApprovalActionRequest(BaseModel):
    action: str = Field(..., description="APPROVE or REJECT")
    notes: Optional[str] = None


# ==================== Response Schemas ====================

class RestoreItemPreview(BaseModel):
    file_id: str
    file_version_id: str
    original_path: str
    target_path: str
    size_bytes: int
    version_number: int
    created_at: str
    has_conflict: bool
    risk_assessment: Dict[str, Any]


class RestorePreviewResponse(BaseModel):
    job_type: str
    total_files: int
    total_bytes: int
    conflicts_count: int
    risk_summary: Dict[str, int]
    requires_approval: bool
    items: List[RestoreItemPreview]


class RecoveryJobItemResponse(BaseModel):
    id: uuid.UUID
    recovery_job_id: uuid.UUID
    file_id: uuid.UUID
    file_version_id: uuid.UUID
    original_path: str
    target_path: str
    status: str
    bytes_restored: int
    sha256_verified: bool
    threat_status: str
    threat_rationale: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecoveryJobResponse(BaseModel):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    target_device_id: Optional[uuid.UUID] = None
    requested_by_id: Optional[uuid.UUID] = None
    job_type: str
    status: str
    snapshot_time: Optional[datetime] = None
    destination_path: str
    destination_type: str
    overwrite_policy: str
    total_files: int
    files_restored: int
    files_failed: int
    files_skipped: int
    bytes_restored: int
    error_message: Optional[str] = None
    requires_approval: bool
    approval_request_id: Optional[uuid.UUID] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: Optional[List[RecoveryJobItemResponse]] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _read_loaded_attributes_only(cls, data: Any) -> Any:
        # Avoid lazy-loading the `items` relationship on an AsyncSession (MissingGreenlet).
        state = sa_inspect(data, raiseerr=False)
        if state is None or "items" not in state.unloaded:
            return data
        return {col.key: getattr(data, col.key) for col in data.__table__.columns}


class RecoveryJobListResponse(BaseModel):
    items: List[RecoveryJobResponse]
    total: int
    page: int
    page_size: int


class RecoveryPointOption(BaseModel):
    snapshot_time: datetime
    total_files: int
    risk_label: str
    threat_summary: str

