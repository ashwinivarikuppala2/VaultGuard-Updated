import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.role import RoleType
from app.models.user import User
from app.schemas.protected_folder import (
    ProtectedFolderCreate,
    ProtectedFolderResponse,
)
from app.security.rbac import get_current_user, require_roles
from app.services.protected_folder_service import ProtectedFolderService

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[ProtectedFolderResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles([RoleType.ADMIN, RoleType.EMPLOYEE, RoleType.INDIVIDUAL]))],
)
async def create_protected_folder(
    request: Request,
    folder_in: ProtectedFolderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ProtectedFolderResponse]:
    """Register a directory path on a device for automated backup protection."""
    service = ProtectedFolderService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    folder = await service.create_protected_folder(
        folder_in=folder_in,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=folder.model_dump(), trace_id=trace_id)


@router.get("", response_model=ApiResponse[List[ProtectedFolderResponse]])
async def list_protected_folders(
    request: Request,
    device_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[ProtectedFolderResponse]]:
    """List monitored directories configured for automated backup protection."""
    service = ProtectedFolderService(db)
    folders = await service.list_protected_folders(
        current_user=current_user, device_id=device_id
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=[f.model_dump() for f in folders], trace_id=trace_id)


@router.delete(
    "/{folder_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_roles([RoleType.ADMIN, RoleType.EMPLOYEE, RoleType.INDIVIDUAL]))],
)
async def delete_protected_folder(
    request: Request,
    folder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    """Remove a directory path from automated backup monitoring."""
    service = ProtectedFolderService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await service.delete_protected_folder(
        folder_id=folder_id,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data={"message": "Protected folder removed successfully"}, trace_id=trace_id)

