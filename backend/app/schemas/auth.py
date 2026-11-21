import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    organization_name: Optional[str] = Field(default=None, min_length=2, max_length=150)


class PersonalRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)


class OrgAdminRegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    storage_quota_bytes: int = Field(default=107374182400, ge=1073741824)
    max_devices: int = Field(default=50, ge=1, le=10000)


class EmployeeJoinRequest(BaseModel):
    invite_code: str = Field(min_length=6, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)


class InviteCodeValidateResponse(BaseModel):
    is_valid: bool
    organization_name: Optional[str] = None
    organization_slug: Optional[str] = None
    message: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    invite_code: Optional[str] = None
    organization_name: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

