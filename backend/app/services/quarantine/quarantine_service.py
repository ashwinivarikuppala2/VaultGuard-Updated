import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_quarantine_triggered_event
from app.models.audit_log import AuditLog
from app.models.device import Device, DeviceStatus
from app.models.future_placeholders import FileVersion
from app.models.threat import Alert, QuarantineEvent, QuarantineIsolationLevel, ThreatLevel
from app.services.alerts.alert_service import alert_service
from app.services.network_monitor.network_service import network_monitor
from app.services.process_monitor.process_service import process_monitor

logger = logging.getLogger("vaultguard.quarantine")


class QuarantineService:
    """Manages endpoint and file quarantine isolation, policy enforcement, and release."""

    async def quarantine_device(
        self,
        db: AsyncSession,
        device_id: uuid.UUID,
        reason: str,
        quarantined_by_id: Optional[uuid.UUID] = None,
        suspect_pid: Optional[int] = None,
        detection_id: Optional[uuid.UUID] = None,
    ) -> QuarantineEvent:
        """
        Enforce immediate host isolation on an endpoint:
        1. Set device status to QUARANTINED.
        2. Create active QuarantineEvent.
        3. Terminate suspect process if PID is provided.
        4. Trigger network isolation.
        5. Write immutable audit log.
        6. Dispatch Module 4 recovery event hook.
        """
        device_res = await db.execute(select(Device).where(Device.id == device_id))
        device = device_res.scalar_one_or_none()
        if not device:
            raise ValueError(f"Device with id '{device_id}' not found.")

        # 1. Update Device status
        device.status = DeviceStatus.QUARANTINED
        logger.warning(f"[QUARANTINE ENFORCED] Device {device.device_id} ({device.name}) isolated: {reason}")

        # 2. Terminate hostile process if provided
        process_outcome = "No process terminated"
        if suspect_pid and suspect_pid > 4:
            success, msg = process_monitor.terminate_process(suspect_pid)
            process_outcome = f"PID {suspect_pid}: {msg}"

        # 3. Network isolation
        network_isolation = network_monitor.isolate_network(str(device_id))

        # 4. Create QuarantineEvent
        event = QuarantineEvent(
            organization_id=device.organization_id,
            device_id=device.id,
            detection_id=detection_id,
            reason=f"{reason} [{process_outcome}]",
            isolation_level=QuarantineIsolationLevel.ENDPOINT.value,
            is_active=True,
            quarantined_by_id=quarantined_by_id,
        )
        db.add(event)

        # 5. Create High-Severity Alert
        alert = Alert(
            organization_id=device.organization_id,
            device_id=device.id,
            detection_id=detection_id,
            title=f"ENDPOINT QUARANTINED: {device.name}",
            description=f"Device {device.device_id} isolated under quarantine policy: {reason}. {process_outcome}",
            severity=ThreatLevel.CRITICAL.value,
            status="NEW",
        )
        db.add(alert)

        # 6. Immutable Audit Log
        audit = AuditLog(
            organization_id=device.organization_id,
            user_id=quarantined_by_id,
            action="DEVICE_QUARANTINED",
            resource_type="Device",
            resource_id=str(device.id),
            details={
                "device_id": str(device.id),
                "device_code": device.device_id,
                "reason": reason,
                "process_outcome": process_outcome,
                "network_isolation": network_isolation,
                "detection_id": str(detection_id) if detection_id else None,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(event)

        # 7. Dispatch Module 4 recovery event hook
        await publish_quarantine_triggered_event({
            "device_id": str(device.id),
            "organization_id": str(device.organization_id),
            "quarantine_event_id": str(event.id),
            "reason": reason,
            "isolation_level": event.isolation_level,
            "timestamp": event.created_at.isoformat(),
        })

        # Broadcast update to web clients
        await alert_service.broadcast({
            "type": "DEVICE_QUARANTINED",
            "device_id": str(device.id),
            "reason": reason,
            "status": "QUARANTINED",
        })

        return event

    async def release_device(
        self,
        db: AsyncSession,
        device_id: uuid.UUID,
        released_by_id: uuid.UUID,
        notes: str = "Host verified clean by security operator.",
    ) -> Optional[QuarantineEvent]:
        """Release an endpoint from quarantine isolation."""
        device_res = await db.execute(select(Device).where(Device.id == device_id))
        device = device_res.scalar_one_or_none()
        if not device:
            return None

        device.status = DeviceStatus.ONLINE

        # Deactivate all active quarantine events for this device
        q_res = await db.execute(
            select(QuarantineEvent).where(
                QuarantineEvent.device_id == device_id,
                QuarantineEvent.is_active == True,
            )
        )
        active_events = q_res.scalars().all()
        last_event = None

        for event in active_events:
            event.is_active = False
            event.restored_at = datetime.now(timezone.utc)
            event.restored_by_id = released_by_id
            last_event = event

        # Immutable Audit Log
        audit = AuditLog(
            organization_id=device.organization_id,
            user_id=released_by_id,
            action="DEVICE_RELEASED_FROM_QUARANTINE",
            resource_type="Device",
            resource_id=str(device.id),
            details={"notes": notes},
        )
        db.add(audit)

        await db.commit()
        if last_event:
            await db.refresh(last_event)

        logger.info(f"[QUARANTINE RELEASED] Device {device.device_id} restored to normal operations.")

        await alert_service.broadcast({
            "type": "DEVICE_RELEASED",
            "device_id": str(device.id),
            "status": "ONLINE",
        })
        return last_event

    async def list_quarantine_events(
        self,
        db: AsyncSession,
        organization_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        device_ids: Optional[List[uuid.UUID]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List active or historical quarantine records."""
        query = select(QuarantineEvent)
        count_query = select(func.count(QuarantineEvent.id))

        if organization_id:
            query = query.where(QuarantineEvent.organization_id == organization_id)
            count_query = count_query.where(QuarantineEvent.organization_id == organization_id)
        if is_active is not None:
            query = query.where(QuarantineEvent.is_active == is_active)
            count_query = count_query.where(QuarantineEvent.is_active == is_active)
        if device_ids is not None:
            query = query.where(QuarantineEvent.device_id.in_(device_ids))
            count_query = count_query.where(QuarantineEvent.device_id.in_(device_ids))

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(QuarantineEvent.created_at)).offset(skip).limit(limit)
        items_res = await db.execute(query)
        events = items_res.scalars().all()

        return {
            "total": total,
            "items": events,
            "skip": skip,
            "limit": limit,
        }


quarantine_service = QuarantineService()

