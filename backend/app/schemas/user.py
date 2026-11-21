import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.role import RoleType


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    organization_id: Optional[uuid.UUID] = None
    role_type: RoleType = RoleType.EMPLOYEE


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    is_active: Optional[bool] = None
    organization_id: Optional[uuid.UUID] = None
    role_type: Optional[RoleType] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    role: RoleResponse
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

