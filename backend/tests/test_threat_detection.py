import os
import uuid
import pytest
from httpx import AsyncClient

from app.services.detection.entropy import entropy_detector
from app.services.detection.extension import extension_detector
from app.services.detection.rates import rate_tracker
from app.services.detection.yara_detector import yara_detector
from app.services.canary.canary_service import canary_service
from app.services.risk_engine.risk_calculator import risk_engine


# ==================== 1. Shannon Entropy Tests ====================
def test_shannon_entropy_calculation():
    # Uniform / low entropy: repeated single character
    uniform_data = b"A" * 1024
    entropy_low = entropy_detector.calculate_shannon_entropy(uniform_data)
    assert entropy_low == 0.0

    # Normal text file (English text)
    text_data = b"The quick brown fox jumps over the lazy dog. Enterprise cloud backup and recovery system." * 20
    entropy_text = entropy_detector.calculate_shannon_entropy(text_data)
    assert 3.5 <= entropy_text <= 5.0

    # High entropy: pseudo-random / encrypted ciphertext (close to 8.0)
    random_bytes = os.urandom(4096)
    entropy_crypto = entropy_detector.calculate_shannon_entropy(random_bytes)
    assert entropy_crypto >= 7.85

    # Evaluation anomaly test
    score, is_suspicious, msg = entropy_detector.evaluate_entropy_anomaly(random_bytes)
    assert is_suspicious is True
    assert "ciphertext" in msg.lower() or "high entropy" in msg.lower()


# ==================== 2. Extension & Ransomware Pattern Tests ====================
def test_extension_and_double_extension_detection():
    # Known ransomware extensions
    suspicious, ext, _ = extension_detector.evaluate_path("C:/Finance/Q3_Ledger.xlsx.locked")
    assert suspicious is True
    assert ext in (".locked", ".xlsx.locked")

    suspicious, ext, _ = extension_detector.evaluate_path("/data/records/db.sqlite.crypt")
    assert suspicious is True
    assert ext == ".crypt"

    # Suspicious double extension
    suspicious, ext, _ = extension_detector.evaluate_path("C:/Users/Admin/contract.docx.enc")
    assert suspicious is True
    assert ext == ".docx.enc"

    # Benign file extension
    suspicious, ext, _ = extension_detector.evaluate_path("C:/Users/Admin/contract.docx")
    assert suspicious is False


# ==================== 3. Rate Tracker Sliding Window Tests ====================
def test_rate_tracker_sliding_window():
    device_id = f"test-dev-{uuid.uuid4().hex[:8]}"

    # Record 10 write events
    for _ in range(10):
        rate_tracker.record_event(device_id, "write")

    rates = rate_tracker.get_current_rates(device_id)
    assert rates["write_rate"] > 0.0
    assert rates["rename_rate"] == 0.0

    # Anomaly evaluation
    is_anom, _, _ = rate_tracker.evaluate_rate_anomaly(device_id, write_threshold=5.0)
    assert is_anom is True


# ==================== 4. YARA Heuristic & Ransom Note Tests ====================
def test_yara_heuristics_ransom_note():
    # Test ransom note filename and content
    note_content = (
        b"ATTENTION! All your files have been encrypted by VaultGuard LockBit ransomware. "
        b"To recover your data, download Tor browser and visit http://sampletorransomnote123456789.onion "
        b"Pay 0.5 BTC to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    )
    matched, rules, desc = yara_detector.inspect_file("readme_to_decrypt.txt", note_content)
    assert matched is True
    assert "RANSOM_NOTE_FILENAME" in rules
    assert len(rules) >= 2

    # Test shadow copy tampering pattern
    script_content = b"vssadmin.exe delete shadows /all /quiet\nbcdedit /set default recoveryenabled no"
    matched, rules, _ = yara_detector.inspect_file("cleanup.bat", script_content)
    assert matched is True
    assert "SHADOW_COPY_TAMPERING_INDICATOR" in rules


# ==================== 5. Canary Decoy Tripwire Tests ====================
def test_canary_payload_and_token_generation():
    token = canary_service.generate_token()
    assert token.startswith("VG-CANARY-")

    fname, payload, sha256 = canary_service.create_canary_payload("Confidential_Q4_Payroll.xlsx", token)
    assert token.encode("utf-8") in payload
    assert len(sha256) == 64


# ==================== 6. Multi-Signal Risk Engine Tests ====================
def test_multi_signal_risk_engine():
    # Benign activity
    benign_res = risk_engine.evaluate(
        entropy_score=4.2,
        write_rate=5.0,
        rename_rate=0.0,
        delete_rate=0.0,
        extension_match=False,
    )
    assert benign_res.score < 40.0
    assert benign_res.risk_level == "LOW"
    assert benign_res.action == "CONTINUE"

    # Suspicious activity (elevated write rate + elevated entropy)
    medium_res = risk_engine.evaluate(
        entropy_score=7.4,
        write_rate=45.0,
        rename_rate=12.0,
    )
    assert 40.0 <= medium_res.score < 70.0
    assert medium_res.risk_level == "MEDIUM"
    assert medium_res.action == "ALERT"

    # Critical outbreak (Canary tripwire hit)
    critical_res = risk_engine.evaluate(
        canary_hit=True,
        entropy_score=7.9,
    )
    assert critical_res.score >= 85.0
    assert critical_res.risk_level in ("HIGH", "CRITICAL")
    assert critical_res.action == "QUARANTINE"


# ==================== 7. End-to-End API Integration Pipeline Tests ====================
@pytest.mark.asyncio
async def test_module3_threat_pipeline_api(client: AsyncClient):
    # 1. Login as Super Admin
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@vaultguard.internal", "password": "AdminSecurePassword123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Org & Device for Threat Testing
    org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "Module3 Threat Defense Org", "contact_email": "soc@vaultguard.internal"},
        headers=headers,
    )
    org_id = org_res.json()["data"]["id"]

    dev_res = await client.post(
        "/api/v1/devices",
        json={"device_id": "SOC-M3-ENDPOINT", "name": "Threat Test Node", "os": "Windows 11 Pro", "organization_id": org_id},
        headers=headers,
    )
    device_id = dev_res.json()["data"]["id"]

    # 3. Create Threat Heuristic Rule via API
    rule_res = await client.post(
        "/api/v1/threats/threat-rules",
        json={
            "name": "Strict Entropy Barrier",
            "description": "Block any file encryption with entropy above 7.8",
            "rule_type": "ENTROPY",
            "condition": "GREATER_THAN",
            "threshold": 7.8,
            "weight": 40.0,
            "severity": "CRITICAL",
            "action": "QUARANTINE",
            "is_enabled": True,
        },
        headers=headers,
    )
    assert rule_res.status_code == 201

    # 4. List Threat Rules
    rules_list = await client.get("/api/v1/threats/threat-rules", headers=headers)
    assert rules_list.status_code == 200
    assert len(rules_list.json()["data"]) >= 1

    # 5. Send Benign Telemetry Event
    benign_telemetry = await client.post(
        "/api/v1/threats/telemetry",
        json={
            "device_id": device_id,
            "file_path": "C:/Projects/source_code.py",
            "event_type": "FILE_MODIFY",
        },
        headers=headers,
    )
    assert benign_telemetry.status_code == 201
    assert benign_telemetry.json()["data"]["action"] == "CONTINUE"

    # 6. Trigger Quarantine on Device
    quarantine_res = await client.post(
        f"/api/v1/quarantine/{device_id}",
        json={"reason": "Manual operator quarantine test", "suspect_pid": 8844},
        headers=headers,
    )
    assert quarantine_res.status_code == 200
    q_data = quarantine_res.json()["data"]
    assert q_data["is_active"] is True

    # 7. List Active Quarantine Events
    q_list = await client.get("/api/v1/quarantine?is_active=true", headers=headers)
    assert q_list.status_code == 200
    assert q_list.json()["data"]["total"] >= 1

    # 8. List Alerts generated by Quarantine
    alerts_res = await client.get("/api/v1/alerts", headers=headers)
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()["data"]["items"]
    assert len(alerts) >= 1
    target_alert_id = alerts[0]["id"]

    # 9. Acknowledge Alert
    ack_res = await client.post(f"/api/v1/alerts/{target_alert_id}/acknowledge", headers=headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["data"]["status"] == "ACKNOWLEDGED"

    # 10. Threat Analytics Endpoint
    analytics_res = await client.get("/api/v1/threats/threat-analytics", headers=headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()["data"]
    assert analytics["quarantined_endpoints"] >= 1

    # 11. Release Device from Quarantine
    release_res = await client.post(f"/api/v1/quarantine/{device_id}/release", headers=headers)
    assert release_res.status_code == 200
    assert release_res.json()["data"]["is_active"] is False
