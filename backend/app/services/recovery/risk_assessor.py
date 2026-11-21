import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.future_placeholders import File, FileVersion
from app.models.recovery import ThreatRiskLabel
from app.models.threat import Detection, DetectionEvent, QuarantineEvent

logger = logging.getLogger("vaultguard.recovery.risk")


class ThreatRiskAssessment:
    """Detailed risk assessment outcome for a candidate recovery version."""

    def __init__(
        self,
        risk_label: str,
        rationale: str,
        evidence: Optional[Dict[str, Any]] = None,
        is_safe_to_restore: bool = True,
    ):
        self.risk_label = risk_label
        self.rationale = rationale
        self.evidence = evidence or {}
        self.is_safe_to_restore = is_safe_to_restore

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_label": self.risk_label,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "is_safe_to_restore": self.is_safe_to_restore,
        }


class RecoveryRiskAssessor:
    """
    Evaluates historical backup versions against Module 3 threat intelligence
    and detection history to flag potentially compromised recovery points.
    """

    async def assess_version_risk(
        self,
        db: AsyncSession,
        version: FileVersion,
        file: Optional[File] = None,
    ) -> ThreatRiskAssessment:
        """
        Assesses whether a backup version was created before or after ransomware/malware activity.
        """
        # If version was explicitly marked quarantined
        if version.is_quarantined:
            return ThreatRiskAssessment(
                risk_label=ThreatRiskLabel.POTENTIALLY_SUSPICIOUS.value,
                rationale="File version is flagged as quarantined under Module 3 policy.",
                evidence={"is_quarantined": True, "entropy_score": version.entropy_score},
                is_safe_to_restore=False,
            )

        # High entropy check (e.g. > 7.6 indicates potential ciphertext / ransomware payload)
        if version.entropy_score and version.entropy_score >= 7.6:
            return ThreatRiskAssessment(
                risk_label=ThreatRiskLabel.POTENTIALLY_SUSPICIOUS.value,
                rationale=f"Elevated Shannon entropy score ({version.entropy_score:.2f}) indicates encrypted or compressed payload; risk of ransomware ciphertext.",
                evidence={"entropy_score": version.entropy_score},
                is_safe_to_restore=False,
            )

        # Resolve parent file if not provided
        if not file and version.file_id:
            file_res = await db.execute(select(File).where(File.id == version.file_id))
            file = file_res.scalar_one_or_none()

        if not file:
            return ThreatRiskAssessment(
                risk_label=ThreatRiskLabel.INSUFFICIENT_DATA.value,
                rationale="Parent file metadata missing; cannot cross-reference endpoint threat telemetry.",
                evidence={},
                is_safe_to_restore=True,
            )

        # Check if the device is currently quarantined
        q_res = await db.execute(
            select(QuarantineEvent)
            .where(
                QuarantineEvent.device_id == file.device_id,
                QuarantineEvent.is_active == True,
            )
            .order_by(desc(QuarantineEvent.created_at))
        )
        active_quarantine = q_res.scalars().first()

        # Query all detections on the file or device created on or before version creation or around it
        det_filters = [(Detection.device_id == file.device_id) | (Detection.file_id == file.id)]
        if file.organization_id is not None:
            det_filters.append(Detection.organization_id == file.organization_id)
        det_query = select(Detection).where(*det_filters).order_by(Detection.created_at.asc())
        det_res = await db.execute(det_query)
        detections = det_res.scalars().all()

        if not detections:
            if active_quarantine:
                return ThreatRiskAssessment(
                    risk_label=ThreatRiskLabel.INSUFFICIENT_DATA.value,
                    rationale="Endpoint is currently quarantined, but no specific file detection record was mapped.",
                    evidence={"device_quarantined": True, "quarantine_reason": active_quarantine.reason},
                    is_safe_to_restore=False,
                )

            return ThreatRiskAssessment(
                risk_label=ThreatRiskLabel.NO_KNOWN_THREAT.value,
                rationale="No security events logged on this endpoint prior to backup creation. Note: Heuristic detection cannot guarantee complete absence of zero-day threats.",
                evidence={"total_detections": 0},
                is_safe_to_restore=True,
            )

        # Look for earliest detection
        earliest_detection: Optional[Detection] = None
        for d in detections:
            # If detection occurred before or within 1 hour after version creation
            if d.created_at <= version.created_at:
                earliest_detection = d
                break

        if earliest_detection:
            threat_name = getattr(earliest_detection, "threat_name", "Heuristic.Threat")
            risk_score = getattr(earliest_detection, "risk_score", 75.0)
            return ThreatRiskAssessment(
                risk_label=ThreatRiskLabel.POTENTIALLY_SUSPICIOUS.value,
                rationale=(
                    f"Version created after security detection '{threat_name}' (Risk Score: {risk_score:.0f}) "
                    f"on endpoint at {earliest_detection.created_at.isoformat()}."
                ),
                evidence={
                    "detection_id": str(earliest_detection.id),
                    "threat_name": threat_name,
                    "severity": earliest_detection.severity,
                    "risk_score": risk_score,
                    "detection_timestamp": earliest_detection.created_at.isoformat(),
                    "version_timestamp": version.created_at.isoformat(),
                },
                is_safe_to_restore=False,
            )

        # Detections occurred only AFTER version creation
        first_future_detection = detections[0]
        return ThreatRiskAssessment(
            risk_label=ThreatRiskLabel.NO_KNOWN_THREAT.value,
            rationale=(
                f"Backup version was created prior to the earliest recorded incident on this endpoint "
                f"({first_future_detection.created_at.isoformat()}). Likely represents a pre-incident recovery point."
            ),
            evidence={
                "pre_incident_snapshot": True,
                "first_incident_at": first_future_detection.created_at.isoformat(),
                "version_created_at": version.created_at.isoformat(),
            },
            is_safe_to_restore=True,
        )


risk_assessor = RecoveryRiskAssessor()

