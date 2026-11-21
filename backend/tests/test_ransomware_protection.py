import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_ransomware_endpoints_e2e(client: AsyncClient):
    # 1. Login as Super Admin
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@vaultguard.internal", "password": "AdminSecurePassword123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Clean start: no genuine threats, no quarantined files, no fabricated metrics
    status_res = await client.get("/api/v1/ransomware/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()["data"]
    assert status_data["threat_score"] == 0.0
    assert status_data["threat_level"] == "Safe"
    assert status_data["quarantined_files_count"] == 0
    assert status_data["detection_engine_status"] in ("ACTIVE", "NO_ACTIVE_AGENT")
    assert status_data["backup_paused"] is False

    # 3. Explicit simulation button: returns a labelled TEST result
    sim_res = await client.post(
        "/api/v1/ransomware/simulate",
        json={"attack_type": "MASS_ENCRYPTION"},
        headers=headers,
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()["data"]
    assert sim_data["events_generated"] >= 4
    assert sim_data["quarantined_files"] >= 2
    assert "SIMULATION (TEST ONLY)" in sim_res.json()["message"]

    # 4. Simulated records must NOT raise the genuine threat state
    status_res_2 = await client.get("/api/v1/ransomware/status", headers=headers)
    assert status_res_2.status_code == 200
    status_data_2 = status_res_2.json()["data"]
    assert status_data_2["threat_score"] == 0.0
    assert status_data_2["threat_level"] == "Safe"
    assert status_data_2["backup_paused"] is False
    assert status_data_2["quarantined_files_count"] == 0
    assert status_data_2["metrics"]["rapid_encryption_detected"] == 0

    # 5. Simulated events are visible, labelled and marked SIMULATED
    events_res = await client.get("/api/v1/ransomware/events?limit=20", headers=headers)
    assert events_res.status_code == 200
    events = events_res.json()["data"]
    simulated = [e for e in events if e["status"] == "SIMULATED"]
    assert len(simulated) >= 4
    assert all(e["reason"].startswith("[SIMULATION]") for e in simulated)
    assert not any(e["status"] == "ACTIVE" for e in events)

    # 6. Simulation never creates real quarantined files
    q_res = await client.get("/api/v1/ransomware/quarantine", headers=headers)
    assert q_res.status_code == 200
    assert q_res.json()["data"] == []

    # 7. Fetch Threat Forensic Logs
    logs_res = await client.get("/api/v1/ransomware/logs?timeframe=all&severity=ALL", headers=headers)
    assert logs_res.status_code == 200
    assert len(logs_res.json()["data"]) >= 3

    # 8. Reset removes only simulated (TEST) records
    reset_res = await client.delete("/api/v1/ransomware/simulation-data", headers=headers)
    assert reset_res.status_code == 200
    removed = reset_res.json()["data"]
    assert removed["ransomware_events"] >= 4
    events_after = (await client.get("/api/v1/ransomware/events?limit=50", headers=headers)).json()["data"]
    assert not any(e["status"] == "SIMULATED" for e in events_after)

    # 9. Resolve / normalize all genuine threats
    resolve_res = await client.post("/api/v1/ransomware/resolve", headers=headers)
    assert resolve_res.status_code == 200

    # 10. Status remains Safe
    status_res_3 = await client.get("/api/v1/ransomware/status", headers=headers)
    assert status_res_3.status_code == 200
    status_data_3 = status_res_3.json()["data"]
    assert status_data_3["threat_score"] == 0.0
    assert status_data_3["threat_level"] == "Safe"
    assert status_data_3["backup_paused"] is False
