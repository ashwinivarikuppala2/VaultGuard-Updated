import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.role import RoleType
from app.models.user import User
from app.repositories.device_repository import DeviceRepository
from app.schemas.threat import QuarantineDeviceRequest, QuarantineListResponse, QuarantineResponse
from app.security.rbac import get_current_user, require_roles
from app.services.quarantine.quarantine_service import quarantine_service

router = APIRouter()


@router.post(
    "/{device_id}",
    response_model=ApiResponse[QuarantineResponse],
    status_code=status.HTTP_200_OK,
    summary="Isolate an endpoint under quarantine policy",
)
async def quarantine_endpoint(
    device_id: uuid.UUID,
    payload: QuarantineDeviceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN, RoleType.INDIVIDUAL])),
):
    try:
        event = await quarantine_service.quarantine_device(
            db=db,
            device_id=device_id,
            reason=payload.reason,
            quarantined_by_id=current_user.id,
            suspect_pid=payload.suspect_pid,
        )
        return success_response(
            data=QuarantineResponse.model_validate(event),
            message="Endpoint successfully isolated under quarantine.",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/{device_id}/release",
    response_model=ApiResponse[Optional[QuarantineResponse]],
    summary="Release an endpoint from quarantine isolation",
)
async def release_endpoint(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN, RoleType.INDIVIDUAL])),
):
    event = await quarantine_service.release_device(
        db=db,
        device_id=device_id,
        released_by_id=current_user.id,
    )
    if not event:
        raise HTTPException(status_code=404, detail="Active quarantine event or device not found.")
    return success_response(
        data=QuarantineResponse.model_validate(event),
        message="Endpoint successfully released from quarantine.",
    )


@router.get(
    "",
    response_model=ApiResponse[QuarantineListResponse],
    summary="List active or historical quarantine records",
)
async def list_quarantine_events(
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device_ids = None
    org_id = None
    if current_user.role.name in [RoleType.INDIVIDUAL.value, RoleType.EMPLOYEE.value]:
        device_ids = await DeviceRepository(db).list_ids_by_user(
            current_user.id, current_user.organization_id
        )
        if not device_ids:
            data = QuarantineListResponse(total=0, items=[], skip=skip, limit=limit)
            return success_response(data=data, message="Quarantine events retrieved successfully.")
    elif current_user.role.name == RoleType.ADMIN.value:
        org_id = current_user.organization_id
        device_repository = DeviceRepository(db)
        device_ids = await device_repository.list_ids_by_user(
            current_user.id, current_user.organization_id
        )
        if current_user.organization_id:
            device_ids.extend(
                await device_repository.list_employee_ids_by_organization(
                    current_user.organization_id
                )
            )
        device_ids = list(dict.fromkeys(device_ids))

    res = await quarantine_service.list_quarantine_events(
        db=db,
        organization_id=org_id,
        is_active=is_active,
        device_ids=device_ids,
        skip=skip,
        limit=limit,
    )
    items = [QuarantineResponse.model_validate(e) for e in res["items"]]
    data = QuarantineListResponse(
        total=res["total"],
        items=items,
        skip=skip,
        limit=limit,
    )
    return success_response(data=data, message="Quarantine events retrieved successfully.")
