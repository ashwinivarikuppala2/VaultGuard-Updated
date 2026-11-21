import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimeStampedUUIDModel


class RecoveryJobType(str, enum.Enum):
    SINGLE_FILE = "SINGLE_FILE"
    FOLDER = "FOLDER"
    BULK = "BULK"
    POINT_IN_TIME = "POINT_IN_TIME"


class RecoveryJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RecoveryItemStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OverwritePolicy(str, enum.Enum):
    SKIP = "SKIP"
    RENAME = "RENAME"
    OVERWRITE = "OVERWRITE"


class DestinationType(str, enum.Enum):
    SAFE_DIR = "SAFE_DIR"
    ORIGINAL = "ORIGINAL"
    CUSTOM_SAFE_DIR = "CUSTOM_SAFE_DIR"


class ThreatRiskLabel(str, enum.Enum):
    NO_KNOWN_THREAT = "no known threat detected"
    POTENTIALLY_SUSPICIOUS = "potentially suspicious"
    INSUFFICIENT_DATA = "not enough information"


class RecoveryJob(TimeStampedUUIDModel):
    """Orchestration record for file, folder, bulk, or point-in-time recovery operations."""
    __tablename__ = "recovery_jobs"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    target_device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(
        String(50),
        default=RecoveryJobType.SINGLE_FILE.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=RecoveryJobStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    snapshot_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    destination_path: Mapped[str] = mapped_column(
        String(1024),
        default="recovered_files",
        nullable=False,
    )
    destination_type: Mapped[str] = mapped_column(
        String(50),
        default=DestinationType.SAFE_DIR.value,
        nullable=False,
    )
    overwrite_policy: Mapped[str] = mapped_column(
        String(50),
        default=OverwritePolicy.SKIP.value,
        nullable=False,
    )
    total_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_restored: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bytes_restored: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_assessment: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[List["RecoveryJobItem"]] = relationship(
        "RecoveryJobItem",
        back_populates="recovery_job",
        cascade="all, delete-orphan",
    )
    approval_request: Mapped[Optional["ApprovalRequest"]] = relationship(
        "ApprovalRequest",
        foreign_keys=[approval_request_id],
    )


class RecoveryJobItem(TimeStampedUUIDModel):
    """Granular per-file execution and verification record for recovery jobs."""
    __tablename__ = "recovery_job_items"

    recovery_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("file_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    target_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default=RecoveryItemStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    bytes_restored: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sha256_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    threat_status: Mapped[str] = mapped_column(
        String(50),
        default=ThreatRiskLabel.NO_KNOWN_THREAT.value,
        nullable=False,
    )
    threat_rationale: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    recovery_job: Mapped["RecoveryJob"] = relationship("RecoveryJob", back_populates="items")


class ApprovalRequest(TimeStampedUUIDModel):
    """Dual-custody approval request for high-impact recovery operations."""
    __tablename__ = "approval_requests"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

