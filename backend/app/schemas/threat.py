import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------- Telemetry & Event Ingestion ----------------
class TelemetryEventCreate(BaseModel):
    device_id: uuid.UUID
    file_path: str
    event_type: str = Field(default="FILE_MODIFY", description="FILE_MODIFY, FILE_RENAME, FILE_DELETE, CANARY_TOUCH")
    content_base64: Optional[str] = Field(default=None, description="Base64 encoded payload sample for entropy & signature checks")
    old_path: Optional[str] = Field(default=None, description="Original path for rename events")
    pid: Optional[int] = Field(default=None, description="Process ID that performed the operation")
    process_name: Optional[str] = Field(default=None, description="Process binary name")
    cmdline: Optional[str] = Field(default=None, description="Full process command line arguments")


class TelemetryEventResponse(BaseModel):
    event_id: str
    risk_score: float
    risk_level: str
    action: str
    threat_name: str
    reasons: List[str]
    factors: Dict[str, Any]
    detection_id: Optional[str] = None
    quarantine_event_id: Optional[str] = None


class LiveEventItem(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    event_type: str
    file_path: str
    risk_score: float
    entropy_score: float
    write_rate: float
    rename_rate: float
    canary_hit: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Detection Models ----------------
class DetectionResponse(BaseModel):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    device_id: uuid.UUID
    detection_type: str
    threat_name: str
    severity: str
    risk_score: float
    confidence_score: float
    status: str
    details: Optional[Dict[str, Any]] = None
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DetectionListResponse(BaseModel):
    total: int
    items: List[DetectionResponse]
    skip: int
    limit: int


# ---------------- Alert Models ----------------
class AlertResponse(BaseModel):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    device_id: Optional[uuid.UUID] = None
    detection_id: Optional[uuid.UUID] = None
    title: str
    description: str
    severity: str
    status: str
    acknowledged_by_id: Optional[uuid.UUID] = None
    acknowledged_at: Optional[datetime] = None
    resolved_by_id: Optional[uuid.UUID] = None
    resolved_at: Optional[datetime] = None
    mitigation_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    total: int
    items: List[AlertResponse]
    skip: int
    limit: int


class AlertAcknowledgeRequest(BaseModel):
    notes: Optional[str] = None


# ---------------- Quarantine Models ----------------
class QuarantineDeviceRequest(BaseModel):
    reason: str
    suspect_pid: Optional[int] = None


class QuarantineResponse(BaseModel):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    device_id: Optional[uuid.UUID] = None
    reason: str
    isolation_level: str
    is_active: bool
    quarantined_by_id: Optional[uuid.UUID] = None
    created_at: datetime
    restored_at: Optional[datetime] = None
    restored_by_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class QuarantineListResponse(BaseModel):
    total: int
    items: List[QuarantineResponse]
    skip: int
    limit: int


# ---------------- Threat Rules Models ----------------
class ThreatRuleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=3, max_length=255)
    rule_type: str = Field(description="ENTROPY, WRITE_RATE, RENAME_RATE, DELETE_RATE, EXTENSION, CANARY, PROCESS, YARA")
    condition: str = Field(default="GREATER_THAN")
    threshold: float
    weight: float = Field(default=20.0, ge=0.0, le=100.0)
    severity: str = Field(default="HIGH")
    action: str = Field(default="ALERT")
    is_enabled: bool = True


class ThreatRuleResponse(BaseModel):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    name: str
    description: str
    rule_type: str
    condition: str
    threshold: float
    weight: float
    severity: str
    action: str
    is_enabled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Canary Decoy Models ----------------
class CanaryDeployRequest(BaseModel):
    device_id: uuid.UUID
    folder_path: str
    template_name: Optional[str] = None


class CanaryResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    file_path: str
    filename: str
    canary_token: str
    is_tampered: bool
    last_checked_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Threat Analytics ----------------
class ThreatAnalyticsResponse(BaseModel):
    total_detections: int
    active_detections: int
    quarantined_endpoints: int
    canaries_deployed: int
    canaries_tripped: int
    fleet_average_risk_score: float
    alerts_by_severity: Dict[str, int]
    threat_distribution: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
