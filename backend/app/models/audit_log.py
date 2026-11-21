import uuid
from typing import Any, Dict, Optional
from sqlalchemy import ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel


class AuditLog(TimeStampedUUIDModel):
    __tablename__ = "audit_logs"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="audit_logs")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    def __init__(self, *args, **kwargs):
        if "entity_type" in kwargs and "resource_type" not in kwargs:
            kwargs["resource_type"] = kwargs.pop("entity_type")
        if "entity_id" in kwargs and "resource_id" not in kwargs:
            kwargs["resource_id"] = kwargs.pop("entity_id")
        super().__init__(*args, **kwargs)

