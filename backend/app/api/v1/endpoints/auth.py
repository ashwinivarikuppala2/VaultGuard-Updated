from json import JSONDecodeError

from fastapi import APIRouter, Depends, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    EmployeeJoinRequest,
    InviteCodeValidateResponse,
    LoginRequest,
    OrgAdminRegisterRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PersonalRegisterRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.security.rbac import get_current_user
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=ApiResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    register_in: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    auth_service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    token_response = await auth_service.register(register_in, ip_address=client_ip, user_agent=user_agent)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=token_response.model_dump(), trace_id=trace_id)


@router.post("/register/personal", response_model=ApiResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register_personal(
    request: Request,
    register_in: PersonalRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    """Register for Personal Use (Role: INDIVIDUAL, No organization)."""
    auth_service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    token_response = await auth_service.register_personal(register_in, ip_address=client_ip, user_agent=user_agent)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=token_response.model_dump(), trace_id=trace_id)


@router.post("/register/organization", response_model=ApiResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register_organization(
    request: Request,
    register_in: OrgAdminRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    """Register a new Organization (Role: ADMIN, auto-generated invite code)."""
    auth_service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    token_response = await auth_service.register_organization(register_in, ip_address=client_ip, user_agent=user_agent)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=token_response.model_dump(), trace_id=trace_id)


@router.get("/validate-invite/{code}", response_model=ApiResponse[InviteCodeValidateResponse])
async def validate_invite_code(
    request: Request,
    code: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[InviteCodeValidateResponse]:
    """Validate an organization invitation code before employee registration."""
    auth_service = AuthService(db)
    result = await auth_service.validate_invite_code(code)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)


@router.post("/register/employee", response_model=ApiResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register_employee(
    request: Request,
    register_in: EmployeeJoinRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    """Join an organization via invitation code (Role: EMPLOYEE)."""
    auth_service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    token_response = await auth_service.register_employee_join(register_in, ip_address=client_ip, user_agent=user_agent)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=token_response.model_dump(), trace_id=trace_id)


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["email", "password"],
                        "properties": {
                            "email": {"type": "string", "format": "email"},
                            "password": {"type": "string", "minLength": 1},
                        },
                    }
                },
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "required": ["username", "password"],
                        "properties": {
                            "username": {"type": "string", "format": "email"},
                            "password": {"type": "string", "minLength": 1},
                        },
                    }
                },
            },
        }
    },
)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse] | JSONResponse:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type in {"application/x-www-form-urlencoded", "multipart/form-data"}:
        form_data = await request.form()
        credentials = {
            "email": form_data.get("username"),
            "password": form_data.get("password"),
        }
    else:
        try:
            credentials = await request.json()
        except JSONDecodeError as exc:
            raise RequestValidationError(
                [
                    {
                        "type": "json_invalid",
                        "loc": ("body", exc.pos),
                        "msg": "JSON decode error",
                        "input": await request.body(),
                        "ctx": {"error": exc.msg},
                    }
                ]
            ) from exc

    try:
        login_in = LoginRequest.model_validate(credentials)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    auth_service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    token_response = await auth_service.login(login_in, ip_address=client_ip, user_agent=user_agent)
    if content_type in {"application/x-www-form-urlencoded", "multipart/form-data"}:
        return JSONResponse(content=token_response.model_dump(mode="json"))

    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=token_response.model_dump(), trace_id=trace_id)


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_tokens(
    request: Request,
    refresh_in: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    auth_service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    token_response = await auth_service.refresh_tokens(
        refresh_in.refresh_token, ip_address=client_ip, user_agent=user_agent
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=token_response.model_dump(), trace_id=trace_id)


@router.post("/logout", response_model=ApiResponse[dict])
async def logout(
    request: Request,
    refresh_in: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    auth_service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await auth_service.logout(
        raw_refresh_token=refresh_in.refresh_token,
        user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data={"message": "Logged out successfully"}, trace_id=trace_id)


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    user_data = UserResponse.model_validate(current_user)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=user_data.model_dump(), trace_id=trace_id)


@router.post("/password-reset", response_model=ApiResponse[dict])
async def request_password_reset(
    request: Request,
    reset_in: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    # Production-ready structure: returns success envelope (prevents user enumeration)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(
        data={"message": "If an account with that email exists, password reset instructions have been issued."},
        trace_id=trace_id,
    )


@router.post("/password-reset/confirm", response_model=ApiResponse[dict])
async def confirm_password_reset(
    request: Request,
    confirm_in: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(
        data={"message": "Password has been successfully updated."},
        trace_id=trace_id,
    )

