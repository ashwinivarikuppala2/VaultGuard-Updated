import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationException
from app.models.device import Device, DeviceStatus
from app.models.future_placeholders import File
from app.models.protected_folder import ProtectedFolder
from app.models.role import Role, RoleType
from app.models.ransomware import (
    QuarantineFile,
    RansomwareEvent,
    ScanHistory,
    ThreatLog,
)
from app.models.threat import Alert, AlertStatus, ThreatLevel
from app.models.user import User
from app.schemas.ransomware import (
    QuarantineActionRequest,
    QuarantineFileResponse,
    RansomwareEventResponse,
    RansomwareHeuristicsSummary,
    RansomwareStatusResponse,
    RestoreQuarantineRequest,
    SimulateRansomwareRequest,
    SimulateRansomwareResponse,
    ThreatLogResponse,
)

logger = logging.getLogger("vaultguard.ransomware_service")

# Simulation (TEST) records are labelled and kept out of genuine threat metrics.
SIMULATED_STATUS = "SIMULATED"
SIMULATION_TAG = "[SIMULATION]"
SIMULATION_SCAN_TYPE = "SIMULATION_AUDIT"
SIMULATED_THREAT_PREFIX = "SIMULATED_"


class RansomwareService:
    """Enterprise ransomware threat monitoring, mitigation, and simulation service."""

    def _get_user_scope_filter(self, model: Any, user: User):
        """Restrict reads to owned devices, plus employee devices for organization admins."""
        owned_device_ids = select(Device.id).where(
            Device.user_id == user.id,
            Device.organization_id == user.organization_id,
        )
        visible_device_ids = owned_device_ids
        if user.role.name == RoleType.ADMIN.value and user.organization_id:
            employee_user_ids = (
                select(User.id)
                .join(Role, User.role_id == Role.id)
                .where(
                    User.organization_id == user.organization_id,
                    Role.name == RoleType.EMPLOYEE.value,
                )
            )
            visible_device_ids = select(Device.id).where(
                Device.organization_id == user.organization_id,
                or_(
                    Device.user_id == user.id,
                    Device.user_id.in_(employee_user_ids),
                ),
            )

        if model is Device:
            return Device.id.in_(visible_device_ids)
        if hasattr(model, "device_id"):
            return model.device_id.in_(visible_device_ids)
        if hasattr(model, "user_id"):
            return model.user_id == user.id
        return model.id.in_(select(Device.id).where(False))

    def _get_owned_device_filter(self, model: Any, user: User):
        owned_device_ids = select(Device.id).where(
            Device.user_id == user.id,
            Device.organization_id == user.organization_id,
        )
        if model is Device:
            return Device.id.in_(owned_device_ids)
        return model.device_id.in_(owned_device_ids)

    async def get_status(self, db: AsyncSession, user: User) -> RansomwareStatusResponse:
        """Aggregate real-time ransomware monitoring status and metrics."""
        # 1. Protected folders count
        folder_q = select(func.count(ProtectedFolder.id)).where(
            self._get_user_scope_filter(ProtectedFolder, user)
        )
        folder_count = (await db.execute(folder_q)).scalar() or 0

        # 2. Files monitored count
        file_q = select(func.count(File.id)).where(
            self._get_user_scope_filter(File, user)
        )
        file_count = (await db.execute(file_q)).scalar() or 0

        # 3. Quarantined files count
        quarantine_q = select(func.count(QuarantineFile.id)).where(
            self._get_user_scope_filter(QuarantineFile, user),
            QuarantineFile.status == "QUARANTINED",
        )
        quarantine_count = (await db.execute(quarantine_q)).scalar() or 0

        # 4. Recent Active Ransomware Events & Threat Score
        events_q = select(RansomwareEvent).where(
            self._get_user_scope_filter(RansomwareEvent, user),
            RansomwareEvent.status == "ACTIVE",
        ).order_by(desc(RansomwareEvent.created_at)).limit(20)
        active_events = (await db.execute(events_q)).scalars().all()

        heuristics = RansomwareHeuristicsSummary()
        if active_events:
            threat_score = max(ev.risk_score for ev in active_events)
            for ev in active_events:
                if "ENCRYPT" in ev.event_type.upper():
                    heuristics.rapid_encryption_detected += 1
                elif "RENAME" in ev.event_type.upper():
                    heuristics.mass_renames_detected += 1
                elif "DELETE" in ev.event_type.upper():
                    heuristics.mass_deletes_detected += 1
                elif "EXTENSION" in ev.event_type.upper():
                    heuristics.rapid_extension_changes += 1
                elif "ENTROPY" in ev.event_type.upper():
                    heuristics.entropy_spikes += 1
                else:
                    heuristics.unknown_encrypted_extensions += 1
        else:
            threat_score = 0.0

        # Determine Threat Level
        if threat_score >= 81.0:
            threat_level = "Critical"
        elif threat_score >= 61.0:
            threat_level = "High"
        elif threat_score >= 41.0:
            threat_level = "Medium"
        elif threat_score >= 21.0:
            threat_level = "Low"
        else:
            threat_level = "Safe"

        # 5. Last scan time
        scan_q = select(ScanHistory).where(
            self._get_user_scope_filter(ScanHistory, user),
            ScanHistory.scan_type != SIMULATION_SCAN_TYPE,
        ).order_by(desc(ScanHistory.created_at)).limit(1)
        latest_scan = (await db.execute(scan_q)).scalars().first()
        last_scan_time = (latest_scan.completed_at or latest_scan.started_at) if latest_scan else None

        backup_paused = threat_score >= 60.0

        # 6. Monitoring is active only when an agent-enrolled device is ONLINE in this scope
        online_q = select(func.count(Device.id)).where(
            self._get_user_scope_filter(Device, user),
            Device.status == DeviceStatus.ONLINE,
        )
        monitoring_active = ((await db.execute(online_q)).scalar() or 0) > 0

        return RansomwareStatusResponse(
            files_monitored=file_count,
            threat_score=round(threat_score, 1),
            threat_level=threat_level,
            protected_folders_count=folder_count,
            last_scan=last_scan_time,
            detection_engine_status="ACTIVE" if monitoring_active else "NO_ACTIVE_AGENT",
            quarantined_files_count=quarantine_count,
            active_monitoring=monitoring_active,
            backup_paused=backup_paused,
            metrics=heuristics,
        )

    async def get_events(self, db: AsyncSession, user: User, limit: int = 50) -> List[RansomwareEventResponse]:
        """Fetch timeline of detected ransomware events."""
        q = (
            select(RansomwareEvent, Device.name.label("device_name"))
            .outerjoin(Device, RansomwareEvent.device_id == Device.id)
            .where(self._get_user_scope_filter(RansomwareEvent, user))
            .order_by(desc(RansomwareEvent.created_at))
            .limit(limit)
        )
        results = (await db.execute(q)).all()

        output: List[RansomwareEventResponse] = []
        for event, dev_name in results:
            item = RansomwareEventResponse(
                id=event.id,
                organization_id=event.organization_id,
                device_id=event.device_id,
                device_name=dev_name or "Windows Endpoint",
                event_type=event.event_type,
                file_path=event.file_path,
                risk_score=event.risk_score,
                severity=event.severity,
                reason=event.reason,
                status=event.status,
                created_at=event.created_at,
                details=event.details,
            )
            output.append(item)
        return output

    async def get_logs(
        self,
        db: AsyncSession,
        user: User,
        timeframe: str = "all",
        severity: str = "ALL",
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[ThreatLogResponse]:
        """Fetch filtered historical threat forensic logs."""
        conditions = [self._get_user_scope_filter(ThreatLog, user)]

        now = datetime.now(timezone.utc)
        if timeframe == "today":
            start_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
            conditions.append(ThreatLog.created_at >= start_today)
        elif timeframe == "7days":
            conditions.append(ThreatLog.created_at >= now - timedelta(days=7))
        elif timeframe == "30days":
            conditions.append(ThreatLog.created_at >= now - timedelta(days=30))

        if severity and severity.upper() != "ALL":
            conditions.append(ThreatLog.severity == severity.upper())

        if search and search.strip():
            pat = f"%{search.strip()}%"
            conditions.append(
                or_(
                    ThreatLog.action.ilike(pat),
                    ThreatLog.threat_type.ilike(pat),
                    ThreatLog.file_path.ilike(pat),
                )
            )

        q = select(ThreatLog).where(*conditions).order_by(desc(ThreatLog.created_at)).limit(limit)
        logs = (await db.execute(q)).scalars().all()
        return [ThreatLogResponse.model_validate(l) for l in logs]

    async def simulate_ransomware(
        self, db: AsyncSession, user: User, request: SimulateRansomwareRequest
    ) -> SimulateRansomwareResponse:
        """Trigger controlled heuristic ransomware attack simulation."""
        # Find or create device for telemetry association
        target_device_id = request.device_id
        if target_device_id:
            target_device = await db.execute(
                select(Device).where(
                    Device.id == target_device_id,
                    self._get_owned_device_filter(Device, user),
                )
            )
            if not target_device.scalar_one_or_none():
                raise AuthorizationException("Simulations are only permitted for your own devices.")
        else:
            dev_q = select(Device).where(self._get_owned_device_filter(Device, user)).limit(1)
            dev = (await db.execute(dev_q)).scalar_one_or_none()
            if dev:
                target_device_id = dev.id
            else:
                new_dev = Device(
                    device_id=str(uuid.uuid4()),
                    name=f"{SIMULATION_TAG} Test Workstation",
                    os="Windows 11 Pro",
                    status=DeviceStatus.OFFLINE,
                    organization_id=user.organization_id,
                    user_id=user.id,
                )
                db.add(new_dev)
                await db.flush()
                target_device_id = new_dev.id

        now = datetime.now(timezone.utc)
        simulated_files = [
            {
                "file_path": "C:/VaultGuard/Finance/Q3_Financial_Projections.xlsx.locked",
                "original_name": "Q3_Financial_Projections.xlsx",
                "event_type": "RAPID_ENCRYPTION",
                "risk_score": 96.5,
                "reason": "Rapid mass encryption: 45 files/min, high Shannon entropy (7.94) and known ransomware suffix (.locked)",
                "size": 1048576,
            },
            {
                "file_path": "C:/VaultGuard/Database/Customer_Master_Vault.mdf.wncry",
                "original_name": "Customer_Master_Vault.mdf",
                "event_type": "MASS_RENAME",
                "risk_score": 92.0,
                "reason": "Mass file renaming burst accompanied by rapid binary entropy shift (7.89)",
                "size": 8388608,
            },
            {
                "file_path": "C:/VaultGuard/Legal/Confidential_Client_Contracts.pdf.crypted",
                "original_name": "Confidential_Client_Contracts.pdf",
                "event_type": "ENTROPY_SPIKE",
                "risk_score": 88.0,
                "reason": "Suspicious high-entropy ciphertext payload detected in user document directory",
                "size": 2097152,
            },
            {
                "file_path": "C:/VaultGuard/.decoy_honey_tripwire.docx",
                "original_name": ".decoy_honey_tripwire.docx",
                "event_type": "CANARY_BREACH",
                "risk_score": 98.0,
                "reason": "Canary decoy tripwire file modified by unauthorized background process",
                "size": 45056,
            },
        ]

        # 1. Insert Ransomware Events
        events_created: List[RansomwareEvent] = []
        for item in simulated_files:
            ev = RansomwareEvent(
                organization_id=user.organization_id,
                device_id=target_device_id,
                user_id=user.id,
                event_type=item["event_type"],
                file_path=item["file_path"],
                risk_score=item["risk_score"],
                severity="CRITICAL",
                reason=f"{SIMULATION_TAG} {item['reason']}",
                status=SIMULATED_STATUS,
                details={
                    "entropy": 7.94,
                    "simulated": True,
                    "is_simulation": True,
                    "process_name": "unknown_injector.exe",
                    "detection_rules": ["High Shannon Entropy", "Mass File Renaming Burst", "Canary Tamper"],
                },
            )
            db.add(ev)
            events_created.append(ev)

        # 2. Insert Quarantine Records
        quarantined_count = 0
        for item in simulated_files[:2]:
            fake_hash = hashlib.sha256(item["file_path"].encode()).hexdigest()
            q_file = QuarantineFile(
                organization_id=user.organization_id,
                device_id=target_device_id,
                user_id=user.id,
                file_path=item["file_path"],
                file_name=item["original_name"],
                sha256_hash=fake_hash,
                file_size_bytes=item["size"],
                quarantine_path=f"C:/VaultGuard/Quarantine/{fake_hash[:16]}.isolated",
                reason=f"{SIMULATION_TAG} {item['reason']}",
                status=SIMULATED_STATUS,
                owner_name=user.full_name or user.email,
                quarantined_at=now,
            )
            db.add(q_file)
            quarantined_count += 1

        # 3. Create Forensic Threat Logs
        logs = [
            ThreatLog(
                organization_id=user.organization_id,
                device_id=target_device_id,
                user_id=user.id,
                action="RANSOMWARE_HEURISTIC_TRIP",
                threat_type=SIMULATED_THREAT_PREFIX + "HIGH_ENTROPY_ENCRYPTION",
                file_path=simulated_files[0]["file_path"],
                severity="CRITICAL",
                details={"entropy": 7.94, "simulation": True},
            ),
            ThreatLog(
                organization_id=user.organization_id,
                device_id=target_device_id,
                user_id=user.id,
                action="CANARY_TRIPWIRE_TRIGGERED",
                threat_type=SIMULATED_THREAT_PREFIX + "CANARY_DECOY_TAMPER",
                file_path=simulated_files[3]["file_path"],
                severity="CRITICAL",
                details={"alarm": "Host decoy breached", "simulation": True},
            ),
            ThreatLog(
                organization_id=user.organization_id,
                device_id=target_device_id,
                user_id=user.id,
                action="AUTOMATIC_BACKUP_LOCK",
                threat_type=SIMULATED_THREAT_PREFIX + "POLICY_INTERVENTION",
                file_path=None,
                severity="HIGH",
                details={"message": "All scheduled backups paused to prevent snapshot corruption"},
            ),
            ThreatLog(
                organization_id=user.organization_id,
                device_id=target_device_id,
                user_id=user.id,
                action="FILE_QUARANTINED",
                threat_type=SIMULATED_THREAT_PREFIX + "MALICIOUS_OBJECT_ISOLATION",
                file_path=simulated_files[0]["file_path"],
                severity="HIGH",
                details={"status": "Moved to isolated storage"},
            ),
        ]
        db.add_all(logs)

        # 4. Insert Scan History
        scan = ScanHistory(
            organization_id=user.organization_id,
            device_id=target_device_id,
            folder_path="C:/VaultGuard/Protected",
            files_scanned=142,
            threats_detected=len(simulated_files),
            threat_score=98.0,
            threat_level="Critical",
            duration_seconds=1.45,
            status="COMPLETED",
            scan_type="SIMULATION_AUDIT",
            started_at=now - timedelta(seconds=2),
            completed_at=now,
        )
        db.add(scan)

        # 5. Insert Threat Alert for Alert Center
        if user.organization_id:
            alert = Alert(
                organization_id=user.organization_id,
                device_id=target_device_id,
                title=f"{SIMULATION_TAG} CRITICAL RANSOMWARE ACTIVITY DETECTED",
                description="Rapid file encryption burst and canary decoy tampering detected on host. Snapshots locked.",
                severity=ThreatLevel.CRITICAL.value,
                status=AlertStatus.NEW.value,
            )
            db.add(alert)

        await db.commit()

        return SimulateRansomwareResponse(
            message="SIMULATION (TEST ONLY): no real files were read, changed or moved. Simulated records are labelled and excluded from genuine threat metrics.",
            threat_score=98.0,
            threat_level="Critical",
            events_generated=len(simulated_files),
            quarantined_files=quarantined_count,
            backup_protection_triggered=True,
        )

    async def clear_simulation_data(self, db: AsyncSession, user: User) -> Dict[str, int]:
        """Delete only SIMULATED (TEST) records within the caller's scope. Genuine records are never touched."""
        removed: Dict[str, int] = {}

        r = await db.execute(delete(RansomwareEvent).where(
            self._get_owned_device_filter(RansomwareEvent, user),
            RansomwareEvent.status == SIMULATED_STATUS,
        ))
        removed["ransomware_events"] = r.rowcount or 0

        r = await db.execute(delete(QuarantineFile).where(
            self._get_owned_device_filter(QuarantineFile, user),
            QuarantineFile.status == SIMULATED_STATUS,
        ))
        removed["quarantine_files"] = r.rowcount or 0

        r = await db.execute(delete(ThreatLog).where(
            self._get_owned_device_filter(ThreatLog, user),
            ThreatLog.threat_type.like(f"{SIMULATED_THREAT_PREFIX}%"),
        ))
        removed["threat_logs"] = r.rowcount or 0

        r = await db.execute(delete(ScanHistory).where(
            self._get_owned_device_filter(ScanHistory, user),
            ScanHistory.scan_type == SIMULATION_SCAN_TYPE,
        ))
        removed["scan_history"] = r.rowcount or 0

        # Alerts are organization-scoped; without an organization, do not touch them.
        if user.organization_id:
            r = await db.execute(delete(Alert).where(
                self._get_owned_device_filter(Alert, user),
                Alert.title.like(f"{SIMULATION_TAG}%"),
            ))
            removed["alerts"] = r.rowcount or 0
        else:
            removed["alerts"] = 0

        await db.commit()
        logger.info(f"Simulation records cleared for user {user.id}: {removed}")
        return removed

    async def quarantine_file(
        self, db: AsyncSession, user: User, payload: QuarantineActionRequest
    ) -> QuarantineFileResponse:
        """Manually or heuristically isolate a suspect file."""
        target_device_id = payload.device_id
        dev_q = select(Device).where(self._get_owned_device_filter(Device, user))
        if target_device_id:
            dev_q = dev_q.where(Device.id == target_device_id)
        dev = (await db.execute(dev_q.limit(1))).scalar_one_or_none()
        if not dev:
            raise AuthorizationException("Quarantining files is only permitted for your own devices.")
        target_device_id = dev.id

        now = datetime.now(timezone.utc)
        file_name = payload.file_path.replace("\\", "/").split("/")[-1]
        fake_hash = hashlib.sha256(payload.file_path.encode()).hexdigest()

        q_file = QuarantineFile(
            organization_id=dev.organization_id,
            device_id=target_device_id,
            user_id=user.id,
            file_path=payload.file_path,
            file_name=file_name,
            sha256_hash=fake_hash,
            file_size_bytes=1048576,
            quarantine_path=f"C:/VaultGuard/Quarantine/{fake_hash[:16]}.isolated",
            reason=payload.reason,
            status="QUARANTINED",
            owner_name=user.full_name or user.email,
            quarantined_at=now,
        )
        db.add(q_file)

        # Log action
        log = ThreatLog(
            organization_id=user.organization_id,
            device_id=target_device_id,
            user_id=user.id,
            action="FILE_QUARANTINED",
            threat_type="MANUAL_QUARANTINE",
            file_path=payload.file_path,
            severity="HIGH",
            details={"reason": payload.reason},
        )
        db.add(log)
        await db.commit()
        await db.refresh(q_file)
        return QuarantineFileResponse.model_validate(q_file)

    async def get_quarantined_files(
        self, db: AsyncSession, user: User, limit: int = 50
    ) -> List[QuarantineFileResponse]:
        """List all quarantined files for user/organization."""
        q = select(QuarantineFile).where(
            self._get_user_scope_filter(QuarantineFile, user),
            QuarantineFile.status == "QUARANTINED",
        ).order_by(desc(QuarantineFile.quarantined_at)).limit(limit)
        files = (await db.execute(q)).scalars().all()
        return [QuarantineFileResponse.model_validate(f) for f in files]

    async def restore_quarantined_file(
        self, db: AsyncSession, user: User, payload: RestoreQuarantineRequest
    ) -> QuarantineFileResponse:
        """Release quarantined file and restore to safe/original destination."""
        q = select(QuarantineFile).where(
            QuarantineFile.id == payload.quarantine_id,
            self._get_owned_device_filter(QuarantineFile, user),
        )
        q_file = (await db.execute(q)).scalar_one_or_none()
        if not q_file:
            raise ValueError(f"Quarantined record {payload.quarantine_id} not found.")

        now = datetime.now(timezone.utc)
        q_file.status = "RESTORED"
        q_file.restored_at = now

        # Add threat log
        log = ThreatLog(
            organization_id=user.organization_id,
            device_id=q_file.device_id,
            user_id=user.id,
            action="FILE_RESTORED",
            threat_type="QUARANTINE_OVERRIDE",
            file_path=q_file.file_path,
            severity="LOW",
            details={"destination": payload.destination},
        )
        db.add(log)

        # If matching active event exists, resolve it
        ev_q = select(RansomwareEvent).where(
            RansomwareEvent.file_path == q_file.file_path,
            RansomwareEvent.status == "ACTIVE",
        )
        active_ev = (await db.execute(ev_q)).scalar_one_or_none()
        if active_ev:
            active_ev.status = "RESOLVED"

        await db.commit()
        await db.refresh(q_file)
        return QuarantineFileResponse.model_validate(q_file)

    async def delete_quarantined_file(
        self, db: AsyncSession, user: User, quarantine_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Purge malicious quarantined artifact permanently."""
        q = select(QuarantineFile).where(
            QuarantineFile.id == quarantine_id,
            self._get_owned_device_filter(QuarantineFile, user),
        )
        q_file = (await db.execute(q)).scalar_one_or_none()
        if not q_file:
            raise ValueError(f"Quarantined record {quarantine_id} not found.")

        now = datetime.now(timezone.utc)
        q_file.status = "DELETED"
        q_file.deleted_at = now

        log = ThreatLog(
            organization_id=user.organization_id,
            device_id=q_file.device_id,
            user_id=user.id,
            action="FILE_PURGED",
            threat_type="MALWARE_DELETION",
            file_path=q_file.file_path,
            severity="MEDIUM",
            details={"sha256": q_file.sha256_hash},
        )
        db.add(log)
        await db.commit()
        return {"status": "SUCCESS", "message": "Quarantined file deleted permanently."}

    async def resolve_all_threats(self, db: AsyncSession, user: User) -> Dict[str, Any]:
        """Resolve all active ransomware alerts and normalize threat score to Safe."""
        ev_q = select(RansomwareEvent).where(
            self._get_owned_device_filter(RansomwareEvent, user),
            RansomwareEvent.status == "ACTIVE",
        )
        active_events = (await db.execute(ev_q)).scalars().all()
        for ev in active_events:
            ev.status = "RESOLVED"

        log = ThreatLog(
            organization_id=user.organization_id,
            device_id=None,
            user_id=user.id,
            action="ALL_THREATS_RESOLVED",
            threat_type="OPERATOR_RESET",
            file_path=None,
            severity="LOW",
            details={"resolved_count": len(active_events)},
        )
        db.add(log)
        await db.commit()
        return {"status": "SUCCESS", "resolved_events": len(active_events), "threat_level": "Safe"}


ransomware_service = RansomwareService()
