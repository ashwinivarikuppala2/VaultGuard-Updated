import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedUUIDModel


class ThreatLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class QuarantineIsolationLevel(str, enum.Enum):
    ENDPOINT = "ENDPOINT"
    FILE = "FILE"
    NETWORK = "NETWORK"


class RuleType(str, enum.Enum):
    ENTROPY = "ENTROPY"
    WRITE_RATE = "WRITE_RATE"
    RENAME_RATE = "RENAME_RATE"
    DELETE_RATE = "DELETE_RATE"
    EXTENSION = "EXTENSION"
    CANARY = "CANARY"
    PROCESS = "PROCESS"
    YARA = "YARA"


class Detection(TimeStampedUUIDModel):
    """Correlated ransomware anomaly detection with confidence score and incident status."""
    __tablename__ = "detections"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    detection_type: Mapped[str] = mapped_column(String(100), nullable=False)
    threat_name: Mapped[str] = mapped_column(String(150), default="Ransomware.Generic.Heuristic", nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default=ThreatLevel.HIGH.value, index=True)
    risk_score: Mapped[float] = mapped_column(Float, default=75.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False, index=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")  # type: ignore
    device: Mapped["Device"] = relationship("Device")  # type: ignore
    events: Mapped[List["DetectionEvent"]] = relationship("DetectionEvent", back_populates="detection", cascade="all, delete-orphan")
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="detection")
    quarantine_events: Mapped[List["QuarantineEvent"]] = relationship("QuarantineEvent", back_populates="detection")


class DetectionEvent(TimeStampedUUIDModel):
    """Raw telemetry and multi-signal event stream for anomaly correlation."""
    __tablename__ = "detection_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    detection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("detections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    rename_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    write_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    delete_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    entropy_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    extension_mismatch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    canary_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    process_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    process_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    raw_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    detection: Mapped[Optional["Detection"]] = relationship("Detection", back_populates="events")


class Alert(TimeStampedUUIDModel):
    """SOC alert generated upon medium/high/critical threat threshold crossing."""
    __tablename__ = "alerts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    detection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("detections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default=ThreatLevel.MEDIUM.value, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default=AlertStatus.NEW.value, nullable=False, index=True)
    acknowledged_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    mitigation_notes: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Relationships
    detection: Mapped[Optional["Detection"]] = relationship("Detection", back_populates="alerts")


class QuarantineEvent(TimeStampedUUIDModel):
    """Enforced isolation action on endpoint device or specific compromised file."""
    __tablename__ = "quarantine_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    detection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("detections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("file_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    isolation_level: Mapped[str] = mapped_column(String(50), default=QuarantineIsolationLevel.ENDPOINT.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    quarantined_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    restored_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    restored_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    detection: Mapped[Optional["Detection"]] = relationship("Detection", back_populates="quarantine_events")


class ThreatRule(TimeStampedUUIDModel):
    """Configurable heuristic threshold and weighting rule for ransomware scoring."""
    __tablename__ = "threat_rules"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    condition: Mapped[str] = mapped_column(String(50), default="GREATER_THAN", nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=20.0, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default=ThreatLevel.HIGH.value, nullable=False)
    action: Mapped[str] = mapped_column(String(50), default="ALERT", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CanaryFile(TimeStampedUUIDModel):
    """Decoy tripwire file planted in protected directories to catch early encryptors."""
    __tablename__ = "canary_files"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    canary_token: Mapped[str] = mapped_column(String(128), nullable=False)
    is_tampered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    tampered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class RiskScore(TimeStampedUUIDModel):
    """Composite risk score evaluated across all telemetry for an endpoint."""
    __tablename__ = "risk_scores"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(50), default=ThreatLevel.LOW.value, nullable=False, index=True)
    factors: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

