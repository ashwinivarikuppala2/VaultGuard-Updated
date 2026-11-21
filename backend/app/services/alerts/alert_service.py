import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.threat import Alert, AlertStatus, ThreatLevel

logger = logging.getLogger("vaultguard.alerts")


class AlertService:
    """Manages SOC security alerts and real-time operator notification broadcasting."""

    def __init__(self) -> None:
        self._websocket_subscribers: List[Any] = []

    def register_ws(self, ws: Any) -> None:
        if ws not in self._websocket_subscribers:
            self._websocket_subscribers.append(ws)

    def unregister_ws(self, ws: Any) -> None:
        if ws in self._websocket_subscribers:
            self._websocket_subscribers.remove(ws)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast live security alerts to connected WebSocket clients."""
        for ws in list(self._websocket_subscribers):
            try:
                await ws.send_json(message)
            except Exception:
                self.unregister_ws(ws)

    async def create_alert(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        title: str,
        description: str,
        severity: str = ThreatLevel.MEDIUM.value,
        device_id: Optional[uuid.UUID] = None,
        detection_id: Optional[uuid.UUID] = None,
    ) -> Alert:
        """Create and persist a new security alert, broadcasting to live clients."""
        alert = Alert(
            organization_id=organization_id,
            device_id=device_id,
            detection_id=detection_id,
            title=title,
            description=description,
            severity=severity,
            status=AlertStatus.NEW.value,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        # Broadcast live notification
        await self.broadcast({
            "type": "NEW_ALERT",
            "alert": {
                "id": str(alert.id),
                "title": alert.title,
                "severity": alert.severity,
                "status": alert.status,
                "device_id": str(alert.device_id) if alert.device_id else None,
                "created_at": alert.created_at.isoformat(),
            }
        })
        return alert

    async def acknowledge_alert(
        self,
        db: AsyncSession,
        alert_id: uuid.UUID,
        user_id: uuid.UUID,
        organization_id: Optional[uuid.UUID] = None,
    ) -> Optional[Alert]:
        """Acknowledge an active security alert by an authenticated operator."""
        query = select(Alert).where(Alert.id == alert_id)
        if organization_id:
            query = query.where(Alert.organization_id == organization_id)

        result = await db.execute(query)
        alert = result.scalar_one_or_none()
        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED.value
        alert.acknowledged_by_id = user_id
        alert.acknowledged_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(alert)

        await self.broadcast({
            "type": "ALERT_ACKNOWLEDGED",
            "alert_id": str(alert.id),
            "status": alert.status,
            "acknowledged_by": str(user_id),
        })
        return alert

    async def resolve_alert(
        self,
        db: AsyncSession,
        alert_id: uuid.UUID,
        user_id: uuid.UUID,
        notes: str = "",
        organization_id: Optional[uuid.UUID] = None,
    ) -> Optional[Alert]:
        """Mark an alert as resolved with mitigation notes."""
        query = select(Alert).where(Alert.id == alert_id)
        if organization_id:
            query = query.where(Alert.organization_id == organization_id)

        result = await db.execute(query)
        alert = result.scalar_one_or_none()
        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED.value
        alert.resolved_by_id = user_id
        alert.resolved_at = datetime.now(timezone.utc)
        alert.mitigation_notes = notes
        await db.commit()
        await db.refresh(alert)

        await self.broadcast({
            "type": "ALERT_RESOLVED",
            "alert_id": str(alert.id),
            "status": alert.status,
        })
        return alert

    async def list_alerts(
        self,
        db: AsyncSession,
        organization_id: Optional[uuid.UUID] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        device_id: Optional[uuid.UUID] = None,
        device_ids: Optional[List[uuid.UUID]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Paginated list of alerts with filtering."""
        query = select(Alert)
        count_query = select(func.count(Alert.id))

        if organization_id:
            query = query.where(Alert.organization_id == organization_id)
            count_query = count_query.where(Alert.organization_id == organization_id)
        if severity:
            query = query.where(Alert.severity == severity.upper())
            count_query = count_query.where(Alert.severity == severity.upper())
        if status:
            query = query.where(Alert.status == status.upper())
            count_query = count_query.where(Alert.status == status.upper())
        if device_id:
            query = query.where(Alert.device_id == device_id)
            count_query = count_query.where(Alert.device_id == device_id)
        elif device_ids is not None:
            query = query.where(Alert.device_id.in_(device_ids))
            count_query = count_query.where(Alert.device_id.in_(device_ids))

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(Alert.created_at)).offset(skip).limit(limit)
        items_res = await db.execute(query)
        alerts = items_res.scalars().all()

        return {
            "total": total,
            "items": alerts,
            "skip": skip,
            "limit": limit,
        }


alert_service = AlertService()

