import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    contact_email: EmailStr
    max_devices: int = Field(default=50, ge=1, le=10000)
    storage_quota_bytes: int = Field(default=107374182400, ge=1073741824) # Minimum 1GB


class OrganizationCreate(OrganizationBase):
    slug: Optional[str] = Field(default=None, min_length=2, max_length=100)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    contact_email: Optional[EmailStr] = None
    max_devices: Optional[int] = Field(default=None, ge=1, le=10000)
    storage_quota_bytes: Optional[int] = Field(default=None, ge=1073741824)
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    invite_code: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

