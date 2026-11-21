from fastapi import APIRouter
from app.api.v1.endpoints import (
    alerts,
    audit_logs,
    auth,
    backups,
    canary,
    detections,
    devices,
    health,
    organizations,
    protected_folders,
    quarantine,
    ransomware,
    recovery,
    storage,
    threats,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["System Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & RBAC"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(backups.router, prefix="/backups", tags=["Secure Backup Engine"])
api_router.include_router(protected_folders.router, prefix="/protected-folders", tags=["Protected Folders"])
api_router.include_router(storage.router, prefix="/storage", tags=["Storage Analytics"])

# Module 3: Threat Detection, Monitoring, Alerts & Quarantine
api_router.include_router(threats.router, prefix="/threats", tags=["Threat Monitoring & Detection"])
api_router.include_router(detections.router, prefix="/detections", tags=["Detections"])
api_router.include_router(quarantine.router, prefix="/quarantine", tags=["Quarantine Isolation"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alert Center"])
api_router.include_router(canary.router, prefix="/canary", tags=["Canary Decoys"])

# Module 4: Recovery, Restoration, Integrity Verification & Recovery Operations
api_router.include_router(recovery.router, prefix="/recovery", tags=["Recovery & Restoration Engine"])

# Ransomware Threat Defense, Heuristics & Simulation
api_router.include_router(ransomware.router, prefix="/ransomware", tags=["Ransomware Protection"])

# Top-level contract aliases for Module 3 compatibility
api_router.add_api_route("/threat-analytics", threats.get_threat_analytics, methods=["GET"], tags=["Threat Analytics"])
api_router.add_api_route("/threat-rules", threats.create_threat_rule, methods=["POST"], tags=["Threat Rules"])
api_router.add_api_route("/threat-rules", threats.list_threat_rules, methods=["GET"], tags=["Threat Rules"])


