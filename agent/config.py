import os
from pydantic import BaseModel


class AgentConfig(BaseModel):
    server_url: str = os.getenv("VAULTGUARD_SERVER_URL", "http://localhost:8000/api/v1")
    device_id: str = os.getenv("VAULTGUARD_DEVICE_ID", "DEV-LOCAL-001")
    device_name: str = os.getenv("VAULTGUARD_DEVICE_NAME", "Local Workstation")
    os_name: str = os.getenv("VAULTGUARD_OS_NAME", "Windows 11")
    auth_email: str = os.getenv("VAULTGUARD_AUTH_EMAIL", "admin@vaultguard.internal")
    auth_password: str = os.getenv("VAULTGUARD_AUTH_PASSWORD", "AdminSecurePassword123!")
    debounce_seconds: float = float(os.getenv("VAULTGUARD_DEBOUNCE_SECONDS", "2.0"))
    poll_interval_seconds: int = int(os.getenv("VAULTGUARD_POLL_INTERVAL", "300"))
    watch_folders: list[str] = [
        f.strip() for f in os.getenv("VAULTGUARD_WATCH_FOLDERS", "./protected_data").split(",") if f.strip()
    ]


agent_config = AgentConfig()

