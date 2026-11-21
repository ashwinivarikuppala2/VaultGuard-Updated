import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.role import RoleType
from app.models.user import User
from app.schemas.threat import DetectionListResponse, DetectionResponse
from app.security.rbac import get_current_user
from app.services.detection.threat_detection_service import threat_detection_service

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[DetectionListResponse],
    summary="List ransomware and anomaly detections",
)
async def get_detections(
    severity: Optional[str] = Query(None, description="LOW, MEDIUM, HIGH, CRITICAL"),
    status: Optional[str] = Query(None, description="ACTIVE, RESOLVED, FALSE_POSITIVE"),
    device_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id
    res = await threat_detection_service.list_detections(
        db=db,
        organization_id=org_id,
        severity=severity,
        status=status,
        device_id=device_id,
        skip=skip,
        limit=limit,
    )
    items = [DetectionResponse.model_validate(item) for item in res["items"]]
    data = DetectionListResponse(
        total=res["total"],
        items=items,
        skip=skip,
        limit=limit,
    )
    return success_response(data=data, message="Detections retrieved successfully.")
