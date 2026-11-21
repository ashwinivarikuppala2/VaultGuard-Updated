import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device, DeviceStatus
from app.models.threat import Alert, CanaryFile, Detection, QuarantineEvent, RiskScore, ThreatLevel


class ThreatAnalyticsService:
    """Aggregates enterprise threat telemetry, fleet posture, and attack vector analytics."""

    async def get_threat_analytics(
        self,
        db: AsyncSession,
        organization_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Aggregate cross-sectional threat posture metrics."""
        # 1. Total & Active Detections
        det_query = select(func.count(Detection.id))
        act_det_query = select(func.count(Detection.id)).where(Detection.status == "ACTIVE")
        if organization_id:
            det_query = det_query.where(Detection.organization_id == organization_id)
            act_det_query = act_det_query.where(Detection.organization_id == organization_id)

        total_detections = (await db.execute(det_query)).scalar() or 0
        active_detections = (await db.execute(act_det_query)).scalar() or 0

        # 2. Quarantined Devices Count
        q_query = select(func.count(Device.id)).where(Device.status == DeviceStatus.QUARANTINED)
        if organization_id:
            q_query = q_query.where(Device.organization_id == organization_id)
        quarantined_endpoints = (await db.execute(q_query)).scalar() or 0

        # 3. Active Alerts Breakdown
        alert_query = select(Alert.severity, func.count(Alert.id)).where(Alert.status.in_(["NEW", "ACKNOWLEDGED"])).group_by(Alert.severity)
        if organization_id:
            alert_query = alert_query.where(Alert.organization_id == organization_id)
        alert_res = await db.execute(alert_query)
        severity_counts = {sev: 0 for sev in [ThreatLevel.CRITICAL.value, ThreatLevel.HIGH.value, ThreatLevel.MEDIUM.value, ThreatLevel.LOW.value]}
        for sev, count in alert_res.all():
            severity_counts[sev] = count

        # 4. Canary Decoys Status
        canary_total_q = select(func.count(CanaryFile.id))
        canary_tampered_q = select(func.count(CanaryFile.id)).where(CanaryFile.is_tampered == True)
        if organization_id:
            canary_total_q = canary_total_q.where(CanaryFile.organization_id == organization_id)
            canary_tampered_q = canary_tampered_q.where(CanaryFile.organization_id == organization_id)
        canaries_deployed = (await db.execute(canary_total_q)).scalar() or 0
        canaries_tripped = (await db.execute(canary_tampered_q)).scalar() or 0

        # 5. Average Fleet Risk Score
        risk_avg_q = select(func.avg(RiskScore.score))
        if organization_id:
            risk_avg_q = risk_avg_q.where(RiskScore.organization_id == organization_id)
        avg_risk = (await db.execute(risk_avg_q)).scalar() or 0.0

        # 6. Detections Breakdown by Threat Name
        threat_breakdown_q = select(Detection.threat_name, func.count(Detection.id)).group_by(Detection.threat_name)
        if organization_id:
            threat_breakdown_q = threat_breakdown_q.where(Detection.organization_id == organization_id)
        threat_breakdown_res = await db.execute(threat_breakdown_q)
        threat_types = [{"name": name, "count": cnt} for name, cnt in threat_breakdown_res.all()]

        # 7. Timeline Heuristics (Aggregated past 7 days)
        now = datetime.now(timezone.utc)
        timeline = []
        for days_back in range(6, -1, -1):
            day_start = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            t_query = select(func.count(Detection.id)).where(
                Detection.created_at >= day_start,
                Detection.created_at < day_end,
            )
            if organization_id:
                t_query = t_query.where(Detection.organization_id == organization_id)
            cnt = (await db.execute(t_query)).scalar() or 0
            timeline.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "detections": cnt,
            })

        return {
            "total_detections": total_detections,
            "active_detections": active_detections,
            "quarantined_endpoints": quarantined_endpoints,
            "canaries_deployed": canaries_deployed,
            "canaries_tripped": canaries_tripped,
            "fleet_average_risk_score": round(float(avg_risk), 1),
            "alerts_by_severity": severity_counts,
            "threat_distribution": threat_types,
            "timeline": timeline,
        }


threat_analytics_service = ThreatAnalyticsService()

