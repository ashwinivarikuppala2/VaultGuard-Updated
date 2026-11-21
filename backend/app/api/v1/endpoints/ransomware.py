import csv
import io
import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.user import User
from app.schemas.ransomware import (
    QuarantineActionRequest,
    QuarantineFileResponse,
    RansomwareEventResponse,
    RansomwareStatusResponse,
    RestoreQuarantineRequest,
    SimulateRansomwareRequest,
    SimulateRansomwareResponse,
    ThreatLogResponse,
)
from app.security.rbac import get_current_user
from app.services.ransomware_service import ransomware_service

router = APIRouter()


@router.get(
    "/status",
    response_model=ApiResponse[RansomwareStatusResponse],
    summary="Get real-time ransomware protection status, threat score, and heuristics metrics",
)
async def get_ransomware_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    status_data = await ransomware_service.get_status(db=db, user=current_user)
    return success_response(
        data=status_data,
        message="Ransomware protection telemetry retrieved successfully.",
    )


@router.get(
    "/events",
    response_model=ApiResponse[List[RansomwareEventResponse]],
    summary="Get real-time timeline of detected ransomware and anomaly events",
)
async def get_ransomware_events(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    events = await ransomware_service.get_events(db=db, user=current_user, limit=limit)
    return success_response(
        data=events,
        message="Ransomware event timeline retrieved successfully.",
    )


@router.get(
    "/logs",
    response_model=ApiResponse[List[ThreatLogResponse]],
    summary="Get filtered forensic threat and audit logs",
)
async def get_threat_logs(
    timeframe: str = Query("all", description="today, 7days, 30days, all"),
    severity: str = Query("ALL", description="CRITICAL, HIGH, MEDIUM, LOW, ALL"),
    search: Optional[str] = Query(None, description="Search term for logs"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = await ransomware_service.get_logs(
        db=db,
        user=current_user,
        timeframe=timeframe,
        severity=severity,
        search=search,
        limit=limit,
    )
    return success_response(
        data=logs,
        message="Threat logs retrieved successfully.",
    )


@router.get(
    "/logs/export",
    summary="Export threat forensic logs as CSV",
)
async def export_threat_logs(
    timeframe: str = Query("all"),
    severity: str = Query("ALL"),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = await ransomware_service.get_logs(
        db=db,
        user=current_user,
        timeframe=timeframe,
        severity=severity,
        search=search,
        limit=500,
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp (UTC)", "Severity", "Threat Type", "Action", "File Path", "Details"])
    for log in logs:
        writer.writerow([
            log.created_at.isoformat() if log.created_at else "",
            log.severity,
            log.threat_type,
            log.action,
            log.file_path or "N/A",
            str(log.details or {}),
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=vaultguard_threat_logs.csv"},
    )


@router.get(
    "/quarantine",
    response_model=ApiResponse[List[QuarantineFileResponse]],
    summary="List all quarantined malicious or suspicious files",
)
async def get_quarantined_files(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    files = await ransomware_service.get_quarantined_files(db=db, user=current_user, limit=limit)
    return success_response(
        data=files,
        message="Quarantined files list retrieved successfully.",
    )


@router.post(
    "/simulate",
    response_model=ApiResponse[SimulateRansomwareResponse],
    status_code=status.HTTP_200_OK,
    summary="Simulate a realistic ransomware attack pattern to verify proactive protection",
)
async def simulate_ransomware(
    payload: SimulateRansomwareRequest = SimulateRansomwareRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await ransomware_service.simulate_ransomware(db=db, user=current_user, request=payload)
    return success_response(
        data=result,
        message=result.message,
    )


@router.delete(
    "/simulation-data",
    response_model=ApiResponse[Dict[str, int]],
    summary="Delete only simulated (TEST) ransomware records; genuine detections are kept",
)
async def clear_simulation_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    removed = await ransomware_service.clear_simulation_data(db=db, user=current_user)
    return success_response(
        data=removed,
        message="Simulation (TEST) records removed. Genuine detections were not touched.",
    )


@router.post(
    "/quarantine",
    response_model=ApiResponse[QuarantineFileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Manually isolate a suspicious file into sandbox quarantine",
)
async def quarantine_file(
    payload: QuarantineActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q_file = await ransomware_service.quarantine_file(db=db, user=current_user, payload=payload)
    return success_response(
        data=q_file,
        message="File successfully isolated to quarantine.",
    )


@router.post(
    "/restore",
    response_model=ApiResponse[QuarantineFileResponse],
    summary="Restore a quarantined file to verified safe destination",
)
async def restore_quarantined_file(
    payload: RestoreQuarantineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        res = await ransomware_service.restore_quarantined_file(db=db, user=current_user, payload=payload)
        return success_response(
            data=res,
            message="Quarantined file successfully verified and restored.",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/quarantine/{quarantine_id}",
    response_model=ApiResponse[dict],
    summary="Permanently delete a malicious quarantined file",
)
async def delete_quarantined_file(
    quarantine_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        res = await ransomware_service.delete_quarantined_file(db=db, user=current_user, quarantine_id=quarantine_id)
        return success_response(
            data=res,
            message="Quarantined payload purged permanently.",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/resolve",
    response_model=ApiResponse[dict],
    summary="Resolve all active ransomware alerts and normalize threat score",
)
async def resolve_all_threats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await ransomware_service.resolve_all_threats(db=db, user=current_user)
    return success_response(
        data=res,
        message="Threat alerts resolved. System status normalized.",
    )
