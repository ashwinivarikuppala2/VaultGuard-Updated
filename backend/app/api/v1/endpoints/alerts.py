import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.role import RoleType
from app.models.user import User
from app.repositories.device_repository import DeviceRepository
from app.schemas.threat import AlertAcknowledgeRequest, AlertListResponse, AlertResponse
from app.security.rbac import get_current_user, require_roles
from app.services.alerts.alert_service import alert_service

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[AlertListResponse],
    summary="List SOC security alerts with filtering",
)
async def list_alerts(
    severity: Optional[str] = Query(None, description="LOW, MEDIUM, HIGH, CRITICAL"),
    status: Optional[str] = Query(None, description="NEW, ACKNOWLEDGED, RESOLVED, DISMISSED"),
    device_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device_ids = None
    org_id = None
    if current_user.role.name in [RoleType.INDIVIDUAL.value, RoleType.EMPLOYEE.value]:
        dev_repo = DeviceRepository(db)
        user_devices, _ = await dev_repo.list_by_user(user_id=current_user.id)
        owned_ids = [d.id for d in user_devices]
        if not owned_ids:
            data = AlertListResponse(total=0, items=[], skip=skip, limit=limit)
            return success_response(data=data, message="Alerts retrieved successfully.")
        if device_id:
            if device_id not in owned_ids:
                data = AlertListResponse(total=0, items=[], skip=skip, limit=limit)
                return success_response(data=data, message="Alerts retrieved successfully.")
        else:
            device_ids = owned_ids
    elif current_user.role.name == RoleType.ADMIN.value:
        org_id = current_user.organization_id

    res = await alert_service.list_alerts(
        db=db,
        organization_id=org_id,
        severity=severity,
        status=status,
        device_id=device_id,
        device_ids=device_ids,
        skip=skip,
        limit=limit,
    )
    items = [AlertResponse.model_validate(a) for a in res["items"]]
    data = AlertListResponse(total=res["total"], items=items, skip=skip, limit=limit)
    return success_response(data=data, message="Alerts retrieved successfully.")


@router.post(
    "/{id}/acknowledge",
    response_model=ApiResponse[AlertResponse],
    summary="Acknowledge an active security alert",
)
async def acknowledge_alert(
    id: uuid.UUID,
    payload: Optional[AlertAcknowledgeRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN, RoleType.EMPLOYEE, RoleType.INDIVIDUAL])),
):
    org_id = current_user.organization_id
    alert = await alert_service.acknowledge_alert(
        db=db, alert_id=id, user_id=current_user.id, organization_id=org_id
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return success_response(data=AlertResponse.model_validate(alert), message="Alert acknowledged.")


@router.post(
    "/{id}/resolve",
    response_model=ApiResponse[AlertResponse],
    summary="Mark an alert as resolved",
)
async def resolve_alert(
    id: uuid.UUID,
    payload: AlertAcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN, RoleType.EMPLOYEE, RoleType.INDIVIDUAL])),
):
    org_id = current_user.organization_id
    alert = await alert_service.resolve_alert(
        db=db,
        alert_id=id,
        user_id=current_user.id,
        notes=payload.notes or "",
        organization_id=org_id,
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return success_response(data=AlertResponse.model_validate(alert), message="Alert marked as resolved.")
