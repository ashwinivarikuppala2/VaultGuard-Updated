# VaultGuard — Secure Cloud Backup & Recovery System Against Ransomware

**Codename:** VaultGuard  
**Release:** Module 4 of 4 (Recovery, Restoration, Integrity Verification & Recovery Operations)  
**Architecture:** Decoupled Clean Architecture (FastAPI + React + PostgreSQL/SQLite + Redis + MinIO S3 + Celery + Endpoint Agent)

---

## 1. System Overview

VaultGuard is a high-assurance, cloud-native disaster recovery platform engineered specifically to resist and remediate coordinated enterprise ransomware infections.

### Module Progression
- **Module 1 (Foundation):** Multi-tenant enterprise boundaries, RBAC (`SUPER_ADMIN`, `ORG_ADMIN`, `EMPLOYEE`), short-lived JWTs, hashed rotatable Refresh Tokens, BCrypt password hashing, Device fleet registration, MinIO S3 cluster integration, Celery+Redis task queue, immutable audit logs, telemetry dashboard.
- **Module 2 (Secure Backup Engine):** 
  * Real-time file system monitoring (`watchdog`) with thread-safe event debouncing.
  * Streaming client/server compression via `zlib` (level 6) with size ratio calculations.
  * Military-grade **AES-256-GCM** authenticated encryption with unique 12-byte nonces, 16-byte authentication tags, and tenant-isolated HKDF key derivation.
  * SHA-256 integrity digests computed on pre-encryption plaintext.
  * Strict S3 storage hierarchy: `<org_id>/<device_id>/<folder_id>/<filename>/<version_number>.enc`.
  * Comprehensive version tracking with monotonically incremented versions.
  * 6 frontend consoles: Backup Center, Backup Jobs, Protected Folders, Version History, Storage Analytics, and Backup Policies.
- **Module 3 (Ransomware Defense, Threat Monitoring & Quarantine):**
  * **Multi-Signal Heuristic Detection Engine:**
    - Shannon Entropy analysis ($H \in [0.0, 8.0]$) flagging encryption bursts ($\ge 7.5$).
    - Real-time sliding window frequency counters for write rate, rename rate, and delete rate.
    - Known ransomware extension matching and double extension detection (`.docx.enc`, `.xlsx.locked`).
    - Canary decoy tripwire files seeded in protected folders with instantaneous tampering alarms.
    - Endpoint process monitoring (`psutil`) detecting shadow copy deletion commands (`vssadmin delete shadows`).
    - Outbound C2 callback monitoring and host network isolation simulation.
    - YARA pattern matching for ransom note signatures and Tor/.onion contact addresses.
  * **Weighted Composite Risk Engine:**
    - Aggregates multi-signal telemetry into a normalized risk score ($0 - 100$).
    - Policy thresholds:
      * **Low (0 - 39):** Normal operations, continuous backup uploads.
      * **Medium (40 - 69):** Creates active SOC alert for operator investigation.
      * **High / Critical (70 - 100):** Automated host containment — isolates endpoint (`DeviceStatus.QUARANTINED`), terminates hostile process, halts cloud backup uploads to safeguard archives, writes immutable audit log.
  * **Real-time Telemetry & WebSocket Event Bus:**
    - Live WebSocket channel (`/api/v1/threats/ws`) broadcasting sub-second security events to SOC dashboards.
  * **7 Enterprise Frontend Consoles:**
    - Threat Dashboard, Detection History, Live Telemetry Stream, Alert Center, Quarantine Center, Threat Analytics, and Risk Policies.
- **Module 4 (Recovery, Restoration, Integrity Verification & Recovery Operations):**
  * **Comprehensive Recovery Modes:**
    - **Single-File Restore:** Specific historical version restoration to safe directory or original location.
    - **Folder Restore:** Hierarchical directory tree restoration preserving relative folder paths.
    - **Local Destination:** Employees can select a computer folder with the browser's native folder picker; verified files are written there after permission and collision checks. Browsers without folder-write support download the restored file or a ZIP archive instead.
    - **Bulk Restore:** Multi-file batch recovery with bounded concurrency and safeguard limits.
    - **Point-in-Time Recovery:** Rollback endpoint or organization to the latest eligible backup versions as of a specified incident timestamp.
  * **Cryptographic Decryption & Plaintext Integrity Verification:**
    - Reverse pipeline: MinIO ciphertext retrieval $\to$ AES-256-GCM authenticated decryption $\to$ zlib decompression.
    - Validates computed SHA-256 digest of decrypted plaintext against stored `file_hash_sha256` before write.
    - Zero untrusted output: Corrupted ciphertext or tampered tags immediately discard plaintext.
  * **Path Traversal Defense & Atomic Safe Staging:**
    - Strict boundary enforcement preventing directory traversal (`../`, `..\\`), null-byte injection, and critical system root overwrites.
    - Temporary staging directory lifecycle (`.recovery_staging/<job_id>`) with atomic commit.
    - Collision policies: `SKIP` (prevent accidental overwrite), `RENAME` (`file (1).ext`), or `OVERWRITE` (explicit authorization).
  * **Module 3 Threat History Integration & Risk Labeling:**
    - Inspects detections and alerts to flag post-incident snapshots as `potentially suspicious`.
    - Discovers pre-incident snapshots labeled `no known threat detected` with explicit evidence.
    - Honest security labeling: Never claims a version is "guaranteed clean" (detection cannot guarantee absence of zero-days).
  * **Durable Background Recovery Jobs & Dual-Custody Approval:**
    - Asynchronous execution with granular per-file item status tracking (`PENDING`, `IN_PROGRESS`, `VERIFYING`, `COMPLETED`, `SKIPPED`, `FAILED`, `CANCELLED`).
    - Supports idempotent retries of failed items and operator cancellation.
    - Dual-custody authorization (`ApprovalRequest`) with separation of duties for bulk or suspicious restorations.
  * **Frontend Recovery Center:**
    - Full React 18 + Tailwind console with Restoration Workspace, Recovery Point Explorer, and Live Job Execution Log.

---

## 2. Platform Architecture & Layering

```
secure colude backup/
├── agent/                         # VaultGuard Endpoint Client Agent
│   ├── backup_agent/agent.py      # Core agent orchestration (watch -> telemetry -> debounce -> compress -> encrypt -> upload)
│   ├── encryption/crypto.py       # Client-side zlib compression & AES-256-GCM encryption
│   ├── file_monitor/debouncer.py  # Thread-safe event debounce queue
│   ├── file_monitor/watcher.py    # Watchdog filesystem observer
│   ├── scheduler/scheduler.py     # Periodic sweep backup scheduler
│   ├── uploader/client.py         # HTTP uploader with auto-reauth, telemetry reporting & exponential backoff
│   ├── config.py                  # Agent configuration
│   └── main.py                    # Agent CLI entry point
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/      # REST routers (auth, orgs, devices, backups, protected_folders, storage, threats, detections, alerts, quarantine, canary, health, audit)
│   │   ├── core/                  # Config, compression, AES-256-GCM encryption, events dispatcher, responses
│   │   ├── database/              # Async SQLAlchemy 2.0 engine & adaptive SQLite/PostgreSQL session
│   │   ├── middleware/            # Request logging, correlation ID, centralized exception handler
│   │   ├── models/                # Declarative ORM models (roles, users, orgs, devices, protected_folders, files, versions, detections, alerts, quarantine_events, threat_rules, canary_files, risk_scores)
│   │   ├── repositories/          # Generic BaseRepository & typed repositories
│   │   ├── schemas/               # Pydantic v2 validation contracts
│   │   ├── security/              # Password hashing, JWT engine, RBAC dependencies
│   │   ├── services/              # Business logic:
│   │   │   ├── detection/         # Entropy, extension, rates, YARA, and master threat detection service
│   │   │   ├── process_monitor/   # Process inspection & termination service
│   │   │   ├── network_monitor/   # C2 callback detection & network isolation
│   │   │   ├── canary/            # Canary decoy file generator & tripwire service
│   │   │   ├── risk_engine/       # Multi-signal 0-100 risk scoring engine
│   │   │   ├── quarantine/        # Host quarantine isolation & release service
│   │   │   ├── alerts/            # SOC alert triage & WebSocket notification service
│   │   │   └── threat_analytics/  # Attack vector & MITRE posture metrics
│   │   ├── storage/               # MinIO S3 client with offline disk fallback
│   │   ├── tasks/                 # Celery workers for offline deep entropy & canary verification
│   │   └── main.py                # Lifespan manager, seeding, CORS & application mount
│   ├── alembic/                   # Database migrations (0001, 0002, 0003)
│   ├── tests/                     # Pytest suite (compression, AES-GCM, entropy, rates, canary, risk, API pipeline)
│   ├── Dockerfile                 # Python 3.11 container definition
│   └── requirements.txt           # Frozen backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/            # UI components, Modals, Status Badges, Navigation Sidebar
│   │   ├── contexts/              # AuthContext & session state
│   │   ├── layouts/               # DashboardLayout & AuthLayout
│   │   ├── pages/                 # Dashboard, Organizations, Devices, BackupCenter, BackupJobs, ProtectedFolders, VersionHistory, StorageAnalytics, BackupPolicies, ThreatDashboard, DetectionHistory, LiveEvents, AlertCenter, QuarantineCenter, ThreatAnalytics, RiskPolicies, Profile, Settings
│   │   ├── services/              # Axios HTTP services with automatic 401 token refresh & threatService
│   │   └── types/                 # TypeScript interfaces matching backend contracts
│   ├── Dockerfile                 # Multi-stage production Nginx container
│   └── package.json               # React 18, Vite, Tailwind CSS, TanStack Query
├── docker-compose.yml             # 7-container production orchestration
├── .env.example                   # Complete environment variable template
└── README.md                      # System documentation
```

---

## 3. Database Schema Blueprint

Provisioned via Alembic migrations (`0001_initial_schema`, `0002_module2_backup_engine`, `0003_module3_threat_detection`):

| Table | Status | Module | Purpose |
| :--- | :--- | :--- | :--- |
| `roles` | Active | Module 1 | RBAC definitions (`SUPER_ADMIN`, `ORG_ADMIN`, `EMPLOYEE`) |
| `organizations` | Active | Module 1 | Multi-tenant accounts, max device limits, storage quotas |
| `users` | Active | Module 1 | Operator accounts with bcrypt hashes and org linkages |
| `refresh_tokens` | Active | Module 1 | High-entropy SHA-256 hashed rotatable session tokens |
| `devices` | Active | Module 1 | Fleet endpoint enrollment, OS detection, online/offline/quarantined status |
| `audit_logs` | Active | Module 1 | Immutable append-only audit trail with IP & user-agent tracking |
| `protected_folders` | Active | Module 2 | Monitored directories, recursive scanning, scan intervals |
| `files` | Active | Module 2 | Unique tracked files, canonical paths, current version pointers |
| `file_versions` | Active | Module 2 | Monotonically versioned backups, AES-256-GCM nonces, tags, compression ratios, S3 URIs |
| `backup_jobs` | Active | Module 2 | Real-time backup job execution queue (MANUAL, SCHEDULED, CONTINUOUS) |
| `detections` | **Active** | **Module 3** | Correlated ransomware anomaly incidents, risk scores, status |
| `detection_events` | **Active** | **Module 3** | Raw telemetry stream (entropy, write rate, rename rate, canary flags, process info) |
| `alerts` | **Active** | **Module 3** | SOC alerts with SLA tracking, acknowledgement, and resolution notes |
| `quarantine_events`| **Active** | **Module 3** | Enforced endpoint and payload quarantine records with audit trails |
| `threat_rules` | **Active** | **Module 3** | Configurable heuristic thresholds, signal weights, and automated actions |
| `canary_files` | **Active** | **Module 3** | Deployed decoy tripwire files and tamper timestamps |
| `risk_scores` | **Active** | **Module 3** | Real-time 0-100 composite risk scores per endpoint |
| `recovery_jobs` | *Placeholder* | Module 4 | Reserved for Disaster recovery & point-in-time restore |
| `approval_requests`| *Placeholder* | Module 4 | Reserved for Dual-custody recovery approvals |

---

## 4. Module 3: REST & WebSocket API Endpoints

### Threat Detection & Live Telemetry (`/api/v1/threats`)
- `POST /api/v1/threats/telemetry`: Endpoint agent reports real-time file event for heuristic risk scoring.
- `GET /api/v1/threats`: Filtered list of threat incidents.
- `GET /api/v1/threats/live`: Sub-second telemetry event stream.
- `GET /api/v1/threats/threat-analytics`: Enterprise threat distribution, attack vectors, and 7-day timeline.
- `POST /api/v1/threats/threat-rules`: Define or update heuristic detection and risk rules.
- `GET /api/v1/threats/threat-rules`: List active heuristic detection rules.
- `WebSocket /api/v1/threats/ws`: Live WebSocket channel for real-time telemetry streaming and alerts.

### Detections (`/api/v1/detections`)
- `GET /api/v1/detections`: Detailed detection incidents list with multi-signal forensic details.

### Quarantine Management (`/api/v1/quarantine`)
- `POST /api/v1/quarantine/{device_id}`: Enforce immediate endpoint network isolation and backup write freeze.
- `POST /api/v1/quarantine/{device_id}/release`: Release an endpoint from quarantine isolation.
- `GET /api/v1/quarantine`: List active and historical quarantine records.

### Alert Center (`/api/v1/alerts`)
- `GET /api/v1/alerts`: Paginated SOC alert list filtered by severity and status.
- `POST /api/v1/alerts/{id}/acknowledge`: Operator acknowledges an active alert.
- `POST /api/v1/alerts/{id}/resolve`: Operator resolves an alert with mitigation notes.

### Canary Decoy Files (`/api/v1/canary`)
- `POST /api/v1/canary/deploy`: Seed a decoy tripwire file into an endpoint directory.
- `GET /api/v1/canary`: List deployed canary decoy files and tamper statuses.

---

## 5. Running VaultGuard

### Option A: Local Development in VS Code

The platform uses an **adaptive architecture**: when run outside Docker, it seamlessly falls back to local SQLite (`vaultguard.db`) and local encrypted disk storage, enabling full testing without needing live database containers.

#### 1. Backend Server:
```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Super Admin: `admin@vaultguard.internal` / `AdminSecurePassword123!`

#### 2. Frontend Web Application:
```powershell
cd frontend
npm install
npm run dev
```
- Access Dashboard: [http://localhost:5173](http://localhost:5173)

#### 3. Endpoint Agent with Ransomware Defense:
```powershell
python -m agent.main
```

---

### Option B: Running with Docker Compose
```bash
docker compose up -d --build
```
* Web Dashboard: [http://localhost:3000](http://localhost:3000)
* Backend API: [http://localhost:8000/docs](http://localhost:8000/docs)
* MinIO Console: [http://localhost:9001](http://localhost:9001)

ClamAV starts with the backend, initializes its persistent signature database,
and is updated daily by FreshClam. Its TCP port is available only on the Compose
network. Verify service readiness and a real scan from the backend:
```powershell
docker compose up -d --build
docker compose ps clamav backend
docker inspect --format "{{.State.Health.Status}}" vaultguard_clamav
docker compose exec backend python -c "from app.services.scanning.malware_scanner import malware_scanner; result = malware_scanner.scan_bytes(b'VaultGuard connectivity check', 'connectivity.txt'); print(result.status.value); assert result.is_safe"
```

Run the live-daemon integration tests after the stack is healthy:
```powershell
docker compose exec -e RUN_CLAMAV_INTEGRATION_TESTS=1 backend python -m pytest --noconftest tests/test_clamav_integration.py -v
```

---

## 6. Running Tests

Run the full unit and security test suite:
```powershell
# 1. Run Module 4 Recovery Engine, Path Traversal, and SHA-256 Integrity tests:
python -m pytest backend/tests/test_recovery_engine.py -k "not (api or test_recovery_job_execution_service_flow)" -v

# 2. Run Module 3 Threat Detection, Entropy, Canary, and Risk tests:
python -m pytest backend/tests/test_threat_detection.py -k "not api" -v

# 3. Run Module 2 Backup Engine, Encryption, and MinIO tests:
python -m pytest backend/tests/test_backup_engine.py -k "not api" -v

# 4. Run entire multi-module test suite simultaneously:
python -m pytest backend/tests/test_recovery_engine.py backend/tests/test_threat_detection.py backend/tests/test_backup_engine.py -k "not (api or test_recovery_job_execution_service_flow)" -v

# 5. Verify production React + TypeScript + Vite build:
npm run build --prefix frontend
```
