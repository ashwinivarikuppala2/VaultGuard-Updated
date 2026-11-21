import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.device import Device
from app.models.role import RoleType
from app.models.threat import CanaryFile
from app.models.user import User
from app.schemas.threat import CanaryDeployRequest, CanaryResponse
from app.security.rbac import get_current_user, require_roles
from app.services.canary.canary_service import canary_service

router = APIRouter()


@router.post(
    "/deploy",
    response_model=ApiResponse[CanaryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Deploy a canary decoy tripwire file into an endpoint directory",
)
async def deploy_canary(
    payload: CanaryDeployRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN, RoleType.INDIVIDUAL])),
):
    dev_res = await db.execute(select(Device).where(Device.id == payload.device_id))
    device = dev_res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Target device not found.")

    canary = await canary_service.register_canary_file(
        db=db,
        organization_id=device.organization_id,
        device_id=device.id,
        folder_path=payload.folder_path,
        template_name=payload.template_name,
    )
    return success_response(data=CanaryResponse.model_validate(canary), message="Canary decoy deployed.")


@router.get(
    "",
    response_model=ApiResponse[List[CanaryResponse]],
    summary="List deployed canary decoy tripwire files",
)
async def list_canaries(
    device_id: Optional[uuid.UUID] = Query(None),
    is_tampered: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(CanaryFile)
    if current_user.role.name in [RoleType.INDIVIDUAL.value, RoleType.EMPLOYEE.value]:
        from app.models.device import Device
        stmt = stmt.join(Device, CanaryFile.device_id == Device.id).where(Device.user_id == current_user.id)
    elif current_user.role.name == RoleType.ADMIN.value and current_user.organization_id:
        stmt = stmt.where(CanaryFile.organization_id == current_user.organization_id)
    if device_id:
        stmt = stmt.where(CanaryFile.device_id == device_id)
    if is_tampered is not None:
        stmt = stmt.where(CanaryFile.is_tampered == is_tampered)

    res = await db.execute(stmt)
    canaries = res.scalars().all()
    return success_response(
        data=[CanaryResponse.model_validate(c) for c in canaries],
        message="Canary decoys retrieved.",
    )
