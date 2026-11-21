import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.device import DeviceStatus


class DeviceBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    os: str = Field(min_length=2, max_length=100)


class DeviceCreate(DeviceBase):
    device_id: str = Field(min_length=4, max_length=100)
    organization_id: Optional[uuid.UUID] = None


class DeviceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    os: Optional[str] = Field(default=None, min_length=2, max_length=100)
    status: Optional[DeviceStatus] = None


class DeviceResponse(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: str
    status: DeviceStatus
    last_seen: Optional[datetime] = None
    organization_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

