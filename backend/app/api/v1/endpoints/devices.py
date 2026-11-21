from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.device import DeviceStatus
from app.models.role import RoleType
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.device import DeviceCreate, DeviceResponse, DeviceUpdate
from app.security.rbac import get_current_user, require_roles
from app.services.device_service import DeviceService

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[DeviceResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles([RoleType.ADMIN, RoleType.EMPLOYEE, RoleType.INDIVIDUAL]))],
)
async def register_device(
    request: Request,
    device_in: DeviceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DeviceResponse]:
    device_service = DeviceService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    result = await device_service.register_device(
        device_in=device_in,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)


@router.get("", response_model=ApiResponse[PaginatedResponse[DeviceResponse]])
async def list_devices(
    request: Request,
    status: Optional[DeviceStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[DeviceResponse]]:
    device_service = DeviceService(db)
    items, total = await device_service.list_devices(
        current_user=current_user, status=status, skip=skip, limit=limit
    )
    trace_id = getattr(request.state, "trace_id", None)
    data = PaginatedResponse[DeviceResponse](
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )
    return success_response(data=data.model_dump(), trace_id=trace_id)


@router.get("/{device_id}", response_model=ApiResponse[DeviceResponse])
async def get_device(
    request: Request,
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DeviceResponse]:
    device_service = DeviceService(db)
    result = await device_service.get_device(device_id=device_id, current_user=current_user)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)


@router.put(
    "/{device_id}",
    response_model=ApiResponse[DeviceResponse],
    dependencies=[Depends(require_roles([RoleType.ADMIN, RoleType.EMPLOYEE, RoleType.INDIVIDUAL]))],
)
async def update_device(
    request: Request,
    device_id: str,
    device_in: DeviceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DeviceResponse]:
    device_service = DeviceService(db)
    result = await device_service.update_device(
        device_id=device_id, device_in=device_in, current_user=current_user
    )
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)

