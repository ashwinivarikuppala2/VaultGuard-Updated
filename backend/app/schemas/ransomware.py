import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RansomwareHeuristicsSummary(BaseModel):
    rapid_encryption_detected: int = 0
    mass_renames_detected: int = 0
    mass_deletes_detected: int = 0
    rapid_extension_changes: int = 0
    entropy_spikes: int = 0
    unknown_encrypted_extensions: int = 0


class RansomwareStatusResponse(BaseModel):
    files_monitored: int = 0
    threat_score: float = 0.0
    threat_level: str = "Safe"
    protected_folders_count: int = 0
    last_scan: Optional[datetime] = None
    detection_engine_status: str = "ACTIVE"
    quarantined_files_count: int = 0
    active_monitoring: bool = True
    backup_paused: bool = False
    metrics: RansomwareHeuristicsSummary = Field(default_factory=RansomwareHeuristicsSummary)


class RansomwareEventResponse(BaseModel):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    device_id: Optional[uuid.UUID] = None
    device_name: Optional[str] = "Windows Endpoint"
    event_type: str
    file_path: str
    risk_score: float
    severity: str
    reason: str
    status: str
    created_at: datetime
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class QuarantineFileResponse(BaseModel):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    device_id: Optional[uuid.UUID] = None
    file_name: str
    file_path: str
    sha256_hash: str
    file_size_bytes: int
    quarantine_path: str
    owner_name: str
    reason: str
    status: str
    quarantined_at: datetime
    restored_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ThreatLogResponse(BaseModel):
    id: uuid.UUID
    action: str
    threat_type: str
    file_path: Optional[str] = None
    severity: str
    created_at: datetime
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class SimulateRansomwareRequest(BaseModel):
    device_id: Optional[uuid.UUID] = None
    attack_type: Optional[str] = Field(
        default="MASS_ENCRYPTION",
        description="MASS_ENCRYPTION, ENTROPY_SPIKE, RAPID_RENAME, CANARY_TAMPER",
    )


class QuarantineActionRequest(BaseModel):
    file_path: str
    reason: str
    device_id: Optional[uuid.UUID] = None


class RestoreQuarantineRequest(BaseModel):
    quarantine_id: uuid.UUID
    destination: Optional[str] = Field(default="ORIGINAL", description="ORIGINAL, SAFE, or custom path")


class SimulateRansomwareResponse(BaseModel):
    message: str
    threat_score: float
    threat_level: str
    events_generated: int
    quarantined_files: int
    backup_protection_triggered: bool
