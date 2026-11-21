import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import PaginatedResponse


class StartBackupRequest(BaseModel):
    device_id: uuid.UUID
    protected_folder_id: Optional[uuid.UUID] = None
    job_type: str = Field(default="FULL", pattern="^(FULL|INCREMENTAL|MANUAL)$")


class ManualBackupRequest(BaseModel):
    device_id: uuid.UUID
    file_path: str = Field(min_length=1, max_length=1024)
    file_content_base64: str = Field(description="Base64-encoded raw file content for direct API ingest")
    protected_folder_id: Optional[uuid.UUID] = None


class BackupJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    device_id: uuid.UUID
    job_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_files: int
    bytes_processed: int
    files_failed: int
    files_skipped: int
    duration_seconds: float
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FileVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_id: uuid.UUID
    version_number: int
    storage_path: str
    file_hash_sha256: str
    size_bytes: int
    original_size_bytes: int
    compressed_size_bytes: int
    compression_algorithm: str
    encryption_algorithm: str
    is_encrypted: bool
    created_at: datetime
    # Malware scan fields
    scan_status: Optional[str] = None
    backup_blocked: bool = False
    is_ransomware_related: bool = False


class FileHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_path: str
    original_filename: str
    file_size: int
    total_versions: int
    is_deleted: bool
    versions: List[FileVersionResponse]
    created_at: datetime
    updated_at: datetime


class BackupSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_id: uuid.UUID
    file_id: uuid.UUID
    file_path: str
    original_filename: str
    version_number: int
    file_hash_sha256: str
    original_size_bytes: int
    encrypted_size_bytes: int
    storage_path: str
    created_at: datetime


class EmployeeBackupSummary(BaseModel):
    employee_id: uuid.UUID
    full_name: str
    email: str
    is_active: bool
    created_at: datetime
    total_backup_files: int
    storage_used_bytes: int
    last_backup_at: Optional[datetime] = None
    backup_status: str


class EmployeeBackupVersion(BaseModel):
    id: uuid.UUID
    version_number: int
    original_size_bytes: int
    encrypted_size_bytes: int
    file_hash_sha256: str
    is_encrypted: bool
    encryption_algorithm: str
    created_at: datetime


class EmployeeBackupFile(BaseModel):
    id: uuid.UUID
    file_path: str
    original_filename: str
    file_size: int
    total_versions: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    versions: List[EmployeeBackupVersion]


class EmployeeRecoveryHistoryItem(BaseModel):
    id: uuid.UUID
    job_type: str
    status: str
    total_files: int
    files_restored: int
    files_failed: int
    bytes_restored: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class EmployeeBackupProfile(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    organization_id: Optional[uuid.UUID] = None
    is_active: bool
    is_verified: bool
    created_at: datetime


class EmployeeBackupDetails(BaseModel):
    employee: EmployeeBackupProfile
    total_backup_files: int
    storage_used_bytes: int
    last_backup_at: Optional[datetime] = None
    backup_status: str
    files: PaginatedResponse[EmployeeBackupFile]
    recovery_history: PaginatedResponse[EmployeeRecoveryHistoryItem]

