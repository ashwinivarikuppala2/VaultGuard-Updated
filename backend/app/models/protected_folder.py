import uuid
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel


class ProtectedFolder(TimeStampedUUIDModel):
    """Monitored directory configured on a device for automated backup protection."""
    __tablename__ = "protected_folders"

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
    folder_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scan_interval_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    include_patterns: Mapped[str] = mapped_column(String(255), default="*.*", nullable=False)
    exclude_patterns: Mapped[str] = mapped_column(String(255), default="*.tmp,*.log,*.lock", nullable=False)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    device: Mapped["Device"] = relationship("Device")

