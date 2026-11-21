import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_threat_detected_event
from app.models.threat import (
    Alert,
    CanaryFile,
    Detection,
    DetectionEvent,
    RiskScore,
    ThreatLevel,
    ThreatRule,
)
from app.services.alerts.alert_service import alert_service
from app.services.canary.canary_service import canary_service
from app.services.detection.entropy import entropy_detector
from app.services.detection.extension import extension_detector
from app.services.detection.rates import rate_tracker
from app.services.detection.yara_detector import yara_detector
from app.services.process_monitor.process_service import process_monitor
from app.services.quarantine.quarantine_service import quarantine_service
from app.services.risk_engine.risk_calculator import risk_engine

logger = logging.getLogger("vaultguard.threat_detection")


class ThreatDetectionService:
    """Master detection coordinator: ingests multi-signal telemetry, evaluates risk, and triggers policy response."""

    async def process_telemetry_event(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        device_id: uuid.UUID,
        file_path: str,
        event_type: str = "FILE_MODIFY",
        content_sample: Optional[bytes] = None,
        old_path: Optional[str] = None,
        pid: Optional[int] = None,
        process_name: Optional[str] = None,
        cmdline: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Multi-signal pipeline:
        Filesystem event -> Feature extraction -> Risk score -> Policy action (Continue / Alert / Quarantine)
        """
        # 1. Sliding window rate tracking
        rate_key = "rename" if event_type in ("FILE_RENAME", "RENAME") else ("delete" if event_type in ("FILE_DELETE", "DELETE") else "write")
        rate_tracker.record_event(str(device_id), rate_key)
        rates = rate_tracker.get_current_rates(str(device_id))

        # 2. Entropy calculation
        entropy_score = 0.0
        if content_sample:
            entropy_score = entropy_detector.calculate_shannon_entropy(content_sample)

        # 3. Extension inspection
        ext_suspicious, matched_ext, ext_rationale = extension_detector.evaluate_path(file_path, old_path or "")

        # 4. Canary decoy tripwire check
        canary_hit, canary_rec, canary_msg = await canary_service.evaluate_file_tamper(
            db, device_id, file_path, current_content=content_sample
        )

        # 5. Process inspection
        proc_suspicious = False
        proc_details = "Normal"
        if pid or process_name:
            proc_suspicious, proc_details = process_monitor.evaluate_process(
                pid=pid or 0, process_name=process_name, cmdline=cmdline
            )

        # 6. YARA / Ransom note heuristics
        yara_matches: List[str] = []
        if content_sample:
            import os
            _, yara_matches, _ = yara_detector.inspect_file(os.path.basename(file_path), content_sample)

        # 7. Composite Risk Evaluation (0-100)
        risk_result = risk_engine.evaluate(
            entropy_score=entropy_score,
            write_rate=rates["write_rate"],
            rename_rate=rates["rename_rate"],
            delete_rate=rates["delete_rate"],
            extension_match=ext_suspicious,
            extension_name=matched_ext,
            canary_hit=canary_hit,
            process_suspicious=proc_suspicious,
            process_details=proc_details,
            yara_matches=yara_matches,
        )

        # 8. Record raw DetectionEvent
        raw_event = DetectionEvent(
            organization_id=organization_id,
            device_id=device_id,
            event_type=event_type,
            file_path=file_path,
            rename_rate=rates["rename_rate"],
            write_rate=rates["write_rate"],
            delete_rate=rates["delete_rate"],
            entropy_score=entropy_score,
            extension_mismatch=ext_suspicious,
            canary_hit=canary_hit,
            process_id=pid,
            process_name=process_name,
            risk_score=risk_result.score,
            raw_metadata={
                "factors": risk_result.factors,
                "reasons": risk_result.reasons,
                "action": risk_result.action,
            },
        )
        db.add(raw_event)

        # 9. Upsert RiskScore for Device
        risk_record = RiskScore(
            organization_id=organization_id,
            device_id=device_id,
            score=risk_result.score,
            risk_level=risk_result.risk_level,
            factors=risk_result.factors,
            evaluated_at=datetime.now(timezone.utc),
        )
        db.add(risk_record)

        detection_record = None
        quarantine_record = None

        # 10. Execute Policy Action
        if risk_result.action == "QUARANTINE":
            # HIGH / CRITICAL THREAT: Create detection record and isolate endpoint
            detection_record = Detection(
                organization_id=organization_id,
                device_id=device_id,
                detection_type="RANSOMWARE_ENCRYPTION_OUTBREAK" if canary_hit or entropy_score >= 7.8 else "HEURISTIC_ANOMALY",
                threat_name=risk_result.threat_name,
                severity=risk_result.risk_level,
                risk_score=risk_result.score,
                confidence_score=risk_result.confidence_score,
                status="ACTIVE",
                details={
                    "file_path": file_path,
                    "reasons": risk_result.reasons,
                    "factors": risk_result.factors,
                    "rates": rates,
                    "entropy": entropy_score,
                    "pid": pid,
                    "process_name": process_name,
                },
            )
            db.add(detection_record)
            await db.flush()

            # Attach detection_id to event
            raw_event.detection_id = detection_record.id

            # Trigger automated endpoint quarantine isolation
            reason_summary = " | ".join(risk_result.reasons[:2])
            quarantine_record = await quarantine_service.quarantine_device(
                db=db,
                device_id=device_id,
                reason=f"Automated threat defense: {reason_summary}",
                suspect_pid=pid,
                detection_id=detection_record.id,
            )

            # Publish threat event for downstreams
            await publish_threat_detected_event({
                "detection_id": str(detection_record.id),
                "device_id": str(device_id),
                "organization_id": str(organization_id),
                "threat_name": detection_record.threat_name,
                "risk_score": risk_result.score,
                "severity": risk_result.risk_level,
                "file_path": file_path,
                "timestamp": detection_record.created_at.isoformat(),
            })

        elif risk_result.action == "ALERT":
            # MEDIUM THREAT: Create alert for SOC review
            reason_summary = " | ".join(risk_result.reasons[:2])
            await alert_service.create_alert(
                db=db,
                organization_id=organization_id,
                device_id=device_id,
                title=f"Suspicious Anomaly on Endpoint ({risk_result.threat_name})",
                description=f"Path: '{file_path}'. Score: {risk_result.score:.1f}. Factors: {reason_summary}",
                severity=ThreatLevel.MEDIUM.value,
            )

        await db.commit()

        # Broadcast live telemetry event to WebSocket subscribers
        telemetry_payload = {
            "type": "LIVE_TELEMETRY",
            "event": {
                "id": str(raw_event.id),
                "device_id": str(device_id),
                "file_path": file_path,
                "event_type": event_type,
                "risk_score": risk_result.score,
                "risk_level": risk_result.risk_level,
                "entropy_score": entropy_score,
                "write_rate": rates["write_rate"],
                "rename_rate": rates["rename_rate"],
                "canary_hit": canary_hit,
                "action": risk_result.action,
                "created_at": raw_event.created_at.isoformat(),
            }
        }
        await alert_service.broadcast(telemetry_payload)

        return {
            "event_id": str(raw_event.id),
            "risk_score": risk_result.score,
            "risk_level": risk_result.risk_level,
            "action": risk_result.action,
            "threat_name": risk_result.threat_name,
            "reasons": risk_result.reasons,
            "factors": risk_result.factors,
            "detection_id": str(detection_record.id) if detection_record else None,
            "quarantine_event_id": str(quarantine_record.id) if quarantine_record else None,
        }

    async def list_detections(
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
        """Query detection incidents with filtering."""
        query = select(Detection)
        count_query = select(func.count(Detection.id))

        if organization_id:
            query = query.where(Detection.organization_id == organization_id)
            count_query = count_query.where(Detection.organization_id == organization_id)
        if severity:
            query = query.where(Detection.severity == severity.upper())
            count_query = count_query.where(Detection.severity == severity.upper())
        if status:
            query = query.where(Detection.status == status.upper())
            count_query = count_query.where(Detection.status == status.upper())
        if device_id:
            query = query.where(Detection.device_id == device_id)
            count_query = count_query.where(Detection.device_id == device_id)
        elif device_ids is not None:
            query = query.where(Detection.device_id.in_(device_ids))
            count_query = count_query.where(Detection.device_id.in_(device_ids))

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(desc(Detection.created_at)).offset(skip).limit(limit)
        items_res = await db.execute(query)
        items = items_res.scalars().all()

        return {"total": total, "items": items, "skip": skip, "limit": limit}

    async def list_live_events(
        self,
        db: AsyncSession,
        organization_id: Optional[uuid.UUID] = None,
        device_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> List[DetectionEvent]:
        """Retrieve recent telemetry stream events."""
        query = select(DetectionEvent)
        if organization_id:
            query = query.where(DetectionEvent.organization_id == organization_id)
        if device_id:
            query = query.where(DetectionEvent.device_id == device_id)

        query = query.order_by(desc(DetectionEvent.created_at)).limit(limit)
        res = await db.execute(query)
        return list(res.scalars().all())


threat_detection_service = ThreatDetectionService()

