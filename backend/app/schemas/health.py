from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel


class ServiceComponentHealth(BaseModel):
    status: str # "HEALTHY", "DEGRADED", "UNHEALTHY"
    latency_ms: Optional[float] = None
    details: Optional[str] = None


class SystemHealthResponse(BaseModel):
    status: str # "HEALTHY", "DEGRADED", "UNHEALTHY"
    timestamp: datetime
    version: str = "1.0.0"
    environment: str
    services: Dict[str, ServiceComponentHealth]

