import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.role import RoleType
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.schemas.user import UserResponse
from app.security.rbac import get_current_user, require_roles
from app.services.organization_service import OrganizationService

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[OrganizationResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles([RoleType.ADMIN]))],
)
async def create_organization(
    request: Request,
    org_in: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OrganizationResponse]:
    org_service = OrganizationService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    result = await org_service.create_organization(
        org_in, current_user=current_user, ip_address=client_ip, user_agent=user_agent
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)


@router.get("", response_model=ApiResponse[PaginatedResponse[OrganizationResponse]])
async def list_organizations(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[OrganizationResponse]]:
    org_service = OrganizationService(db)
    items, total = await org_service.list_organizations(current_user=current_user, skip=skip, limit=limit)
    trace_id = getattr(request.state, "trace_id", None)
    data = PaginatedResponse[OrganizationResponse](
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )
    return success_response(data=data.model_dump(), trace_id=trace_id)


@router.get("/invite-code", response_model=ApiResponse[dict])
async def get_invite_code(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Retrieve the active organization invitation code (auto-generates if empty)."""
    org_service = OrganizationService(db)
    result = await org_service.get_invite_code(current_user=current_user)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result, trace_id=trace_id)


@router.post(
    "/invite-code/regenerate",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_roles([RoleType.ADMIN]))],
)
async def regenerate_invite_code(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Regenerate a new unique invite code for the organization."""
    org_service = OrganizationService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    result = await org_service.regenerate_invite_code(
        current_user=current_user, ip_address=client_ip, user_agent=user_agent
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result, trace_id=trace_id)


@router.post(
    "/invite-code/generate",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_roles([RoleType.ADMIN]))],
)
async def generate_invite_code(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Explicitly generate an invite code for an organization."""
    org_service = OrganizationService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    result = await org_service.regenerate_invite_code(
        current_user=current_user, ip_address=client_ip, user_agent=user_agent
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result, trace_id=trace_id)


@router.get(
    "/employees",
    response_model=ApiResponse[List[UserResponse]],
    dependencies=[Depends(require_roles([RoleType.ADMIN]))],
)
async def list_organization_employees(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[UserResponse]]:
    """List all employees enrolled under the organization."""
    org_service = OrganizationService(db)
    employees = await org_service.list_employees(current_user=current_user)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=[emp.model_dump() for emp in employees], trace_id=trace_id)


@router.get("/{org_id}", response_model=ApiResponse[OrganizationResponse])
async def get_organization(
    request: Request,
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OrganizationResponse]:
    org_service = OrganizationService(db)
    result = await org_service.get_organization_by_id(org_id=org_id, current_user=current_user)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)


@router.put(
    "/{org_id}",
    response_model=ApiResponse[OrganizationResponse],
    dependencies=[Depends(require_roles([RoleType.ADMIN]))],
)
async def update_organization(
    request: Request,
    org_id: uuid.UUID,
    org_in: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[OrganizationResponse]:
    org_service = OrganizationService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    result = await org_service.update_organization(
        org_id=org_id,
        org_in=org_in,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)


@router.delete(
    "/{org_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_roles([RoleType.ADMIN]))],
)
async def delete_organization(
    request: Request,
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    org_service = OrganizationService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await org_service.delete_organization(
        org_id=org_id,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data={"message": "Organization deleted successfully"}, trace_id=trace_id)

