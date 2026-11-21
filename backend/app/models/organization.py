import secrets
from typing import List, Optional
from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel


def generate_organization_invite_code() -> str:
    """Generate secure, human-readable invite code in format VG-8XH2-LM9Q."""
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    part1 = "".join(secrets.choice(alphabet) for _ in range(4))
    part2 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"VG-{part1}-{part2}"


class Organization(TimeStampedUUIDModel):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        default=generate_organization_invite_code,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_devices: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    storage_quota_bytes: Mapped[int] = mapped_column(BigInteger, default=107374182400, nullable=False) # 100 GB default

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan"
    )
    devices: Mapped[List["Device"]] = relationship(
        "Device", back_populates="organization", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="organization", cascade="all, delete-orphan"
    )

