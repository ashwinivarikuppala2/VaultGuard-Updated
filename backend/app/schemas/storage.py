import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class DeviceStorageUsage(BaseModel):
    device_id: uuid.UUID
    device_name: str
    total_files: int
    total_versions: int
    total_bytes: int


class StorageStatisticsResponse(BaseModel):
    total_files: int
    total_versions: int
    total_original_bytes: int
    total_stored_bytes: int
    space_saved_bytes: int
    compression_savings_percent: float
    active_protected_folders: int
    total_backup_jobs: int
    successful_backup_jobs: int
    failed_backup_jobs: int
    device_breakdown: List[DeviceStorageUsage]

