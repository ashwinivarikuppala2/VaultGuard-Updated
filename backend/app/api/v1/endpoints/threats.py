import base64
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.role import RoleType
from app.models.threat import ThreatRule
from app.models.user import User
from app.schemas.threat import (
    LiveEventItem,
    TelemetryEventCreate,
    TelemetryEventResponse,
    ThreatAnalyticsResponse,
    ThreatRuleCreate,
    ThreatRuleResponse,
)
from app.security.rbac import get_current_user, require_roles
from app.services.alerts.alert_service import alert_service
from app.services.detection.threat_detection_service import threat_detection_service
from app.services.threat_analytics_service import threat_analytics_service

router = APIRouter()


@router.post(
    "/telemetry",
    response_model=ApiResponse[TelemetryEventResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Ingest endpoint filesystem telemetry and evaluate real-time ransomware risk",
)
async def ingest_telemetry(
    payload: TelemetryEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id
    if not org_id:
        from app.models.device import Device
        dev_res = await db.execute(select(Device).where(Device.id == payload.device_id))
        dev = dev_res.scalar_one_or_none()
        if not dev:
            raise HTTPException(status_code=404, detail="Target device not found.")
        org_id = dev.organization_id

    # Decode base64 content if present
    content_sample = None
    if payload.content_base64:
        try:
            content_sample = base64.b64decode(payload.content_base64)
        except Exception:
            content_sample = None

    result = await threat_detection_service.process_telemetry_event(
        db=db,
        organization_id=org_id,
        device_id=payload.device_id,
        file_path=payload.file_path,
        event_type=payload.event_type,
        content_sample=content_sample,
        old_path=payload.old_path,
        pid=payload.pid,
        process_name=payload.process_name,
        cmdline=payload.cmdline,
    )
    return success_response(data=TelemetryEventResponse(**result), message="Telemetry processed successfully.")


@router.get(
    "",
    response_model=ApiResponse[Dict[str, Any]],
    summary="List aggregated threats and anomaly incidents",
)
async def list_threats(
    severity: Optional[str] = Query(None, description="LOW, MEDIUM, HIGH, CRITICAL"),
    status_filter: Optional[str] = Query(None, alias="status"),
    device_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device_ids = None
    org_id = None
    if current_user.role.name in [RoleType.INDIVIDUAL.value, RoleType.EMPLOYEE.value]:
        from app.repositories.device_repository import DeviceRepository
        user_devices, _ = await DeviceRepository(db).list_by_user(user_id=current_user.id)
        device_ids = [d.id for d in user_devices]
        if not device_ids:
            return success_response(
                data={"total": 0, "items": [], "skip": skip, "limit": limit},
                message="Threat detections retrieved successfully.",
            )
    elif current_user.role.name == RoleType.ADMIN.value:
        org_id = current_user.organization_id

    result = await threat_detection_service.list_detections(
        db=db,
        organization_id=org_id,
        severity=severity,
        status=status_filter,
        device_id=device_id,
        device_ids=device_ids,
        skip=skip,
        limit=limit,
    )
    # Format items
    items_data = [
        {
            "id": str(d.id),
            "device_id": str(d.device_id),
            "threat_name": d.threat_name,
            "detection_type": d.detection_type,
            "severity": d.severity,
            "risk_score": d.risk_score,
            "confidence_score": d.confidence_score,
            "status": d.status,
            "details": d.details,
            "is_resolved": d.is_resolved,
            "created_at": d.created_at.isoformat(),
        }
        for d in result["items"]
    ]
    return success_response(
        data={"total": result["total"], "items": items_data, "skip": skip, "limit": limit},
        message="Threats retrieved successfully.",
    )


@router.get(
    "/live",
    response_model=ApiResponse[List[LiveEventItem]],
    summary="Retrieve latest live telemetry stream items",
)
async def get_live_threat_events(
    device_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id
    events = await threat_detection_service.list_live_events(
        db=db, organization_id=org_id, device_id=device_id, limit=limit
    )
    return success_response(
        data=[LiveEventItem.model_validate(e) for e in events],
        message="Live telemetry events retrieved successfully.",
    )


@router.get(
    "/threat-analytics",
    response_model=ApiResponse[ThreatAnalyticsResponse],
    summary="Get enterprise ransomware posture, threat distribution, and analytics",
)
async def get_threat_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id
    analytics = await threat_analytics_service.get_threat_analytics(db=db, organization_id=org_id)
    return success_response(
        data=ThreatAnalyticsResponse(**analytics),
        message="Threat analytics computed successfully.",
    )


@router.post(
    "/threat-rules",
    response_model=ApiResponse[ThreatRuleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Define or update a threat heuristic detection rule",
)
async def create_threat_rule(
    payload: ThreatRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([RoleType.ADMIN, RoleType.INDIVIDUAL])),
):
    rule = ThreatRule(
        organization_id=current_user.organization_id,
        name=payload.name,
        description=payload.description,
        rule_type=payload.rule_type.upper(),
        condition=payload.condition.upper(),
        threshold=payload.threshold,
        weight=payload.weight,
        severity=payload.severity.upper(),
        action=payload.action.upper(),
        is_enabled=payload.is_enabled,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return success_response(data=ThreatRuleResponse.model_validate(rule), message="Threat rule created.")


@router.get(
    "/threat-rules",
    response_model=ApiResponse[List[ThreatRuleResponse]],
    summary="List active threat detection and risk weighting rules",
)
async def list_threat_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ThreatRule)
    if current_user.organization_id:
        stmt = stmt.where((ThreatRule.organization_id == current_user.organization_id) | (ThreatRule.organization_id == None))

    result = await db.execute(stmt)
    rules = result.scalars().all()
    return success_response(data=[ThreatRuleResponse.model_validate(r) for r in rules], message="Threat rules retrieved.")


@router.websocket("/ws")
async def threat_websocket_endpoint(websocket: WebSocket):
    """Bi-directional WebSocket for real-time threat telemetry and alert broadcasting."""
    await websocket.accept()
    alert_service.register_ws(websocket)
    try:
        while True:
            # Keep-alive ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        alert_service.unregister_ws(websocket)
    except Exception:
        alert_service.unregister_ws(websocket)
