import enum
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel


class File(TimeStampedUUIDModel):
    """Monitored file tracked across backup snapshots."""
    __tablename__ = "files"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    protected_folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("protected_folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_versions: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    versions: Mapped[list["FileVersion"]] = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")


class FileVersion(TimeStampedUUIDModel):
    """Encrypted, compressed, immutable file backup version."""
    __tablename__ = "file_versions"

    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    original_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    compressed_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    compression_algorithm: Mapped[str] = mapped_column(String(20), default="zlib", nullable=False)
    encryption_algorithm: Mapped[str] = mapped_column(String(30), default="AES-256-GCM", nullable=False)
    nonce_hex: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    auth_tag_hex: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    entropy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_quarantined: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Malware scan result fields (populated for every version)
    scan_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    scan_detection_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    scan_detection_category: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    scan_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    quarantine_reference: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    backup_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backup_blocked_reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_ransomware_related: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    file: Mapped["File"] = relationship("File", back_populates="versions")


class BackupJob(TimeStampedUUIDModel):
    """Execution record for backup runs (scheduled or manual)."""
    __tablename__ = "backup_jobs"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, default="FULL")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bytes_processed: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    files_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)


class FileScanEvent(TimeStampedUUIDModel):
    """Audit record for every malware scan attempt — created for blocked files that never become FileVersions."""
    __tablename__ = "file_scan_events"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    scan_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    detection_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    detection_category: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_ransomware_related: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quarantine_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    backup_blocked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
    )


from app.models.threat import Detection, QuarantineEvent
from app.models.recovery import RecoveryJob, ApprovalRequest

