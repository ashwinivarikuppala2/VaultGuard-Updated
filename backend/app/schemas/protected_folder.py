import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProtectedFolderBase(BaseModel):
    folder_path: str = Field(min_length=1, max_length=1024)
    scan_interval_seconds: int = Field(default=300, ge=10, le=86400)
    include_patterns: str = Field(default="*.*", max_length=255)
    exclude_patterns: str = Field(default="*.tmp,*.log,*.lock", max_length=255)
    is_active: bool = True


class ProtectedFolderCreate(ProtectedFolderBase):
    device_id: uuid.UUID


class ProtectedFolderUpdate(BaseModel):
    folder_path: Optional[str] = Field(default=None, min_length=1, max_length=1024)
    scan_interval_seconds: Optional[int] = Field(default=None, ge=10, le=86400)
    include_patterns: Optional[str] = None
    exclude_patterns: Optional[str] = None
    is_active: Optional[bool] = None


class ProtectedFolderResponse(ProtectedFolderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    device_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

