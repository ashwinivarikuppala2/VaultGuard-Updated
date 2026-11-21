import base64
import logging
import time
from typing import Any, Dict, Optional
import requests
from agent.config import agent_config

logger = logging.getLogger("vaultguard.agent.uploader")


class VaultGuardAPIClient:
    """Resilient API client with automatic token renewal and exponential backoff."""

    def __init__(self, config=agent_config):
        self.config = config
        self.base_url = config.server_url.rstrip("/")
        self.access_token: Optional[str] = None
        self.device_uuid: Optional[str] = None
        self.session = requests.Session()

    def request_with_retry(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 4,
        backoff_base: float = 1.5,
    ) -> requests.Response:
        """Sends HTTP request with exponential backoff on network errors or 5xx."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        attempt = 0
        last_error = None

        while attempt < max_retries:
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    headers=headers,
                    timeout=30.0,
                )
                if response.status_code == 401 and path != "auth/login":
                    logger.warning("Token expired during request, re-authenticating...")
                    self.authenticate()
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    continue

                if response.status_code >= 500:
                    logger.warning(f"Server 5xx response ({response.status_code}), retrying...")
                else:
                    return response

            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = e
                logger.warning(f"Network error on {url} (attempt {attempt+1}/{max_retries}): {str(e)}")

            attempt += 1
            if attempt < max_retries:
                sleep_sec = backoff_base ** attempt
                time.sleep(sleep_sec)

        if last_error:
            raise last_error
        return response

    def authenticate(self) -> str:
        """Authenticate with the VaultGuard backend and obtain JWT access token."""
        logger.info(f"Authenticating agent with server: {self.config.auth_email}")
        res = self.request_with_retry(
            method="POST",
            path="auth/login",
            json_data={
                "email": self.config.auth_email,
                "password": self.config.auth_password,
            },
        )
        if res.status_code != 200:
            raise RuntimeError(f"Authentication failed ({res.status_code}): {res.text}")

        data = res.json().get("data", {})
        self.access_token = data.get("access_token")
        logger.info("Agent authenticated successfully.")
        return self.access_token

    def enroll_or_get_device(self) -> str:
        """Verify device registration or register with server."""
        if not self.access_token:
            self.authenticate()

        # Check existing device
        res = self.request_with_retry(
            method="GET",
            path=f"devices/{self.config.device_id}",
        )
        if res.status_code == 200:
            dev = res.json().get("data", {})
            self.device_uuid = dev.get("id")
            logger.info(f"Device already enrolled: {self.config.device_id} (UUID: {self.device_uuid})")
            return self.device_uuid

        # Register device
        logger.info(f"Enrolling device: {self.config.device_id}")
        reg_res = self.request_with_retry(
            method="POST",
            path="devices",
            json_data={
                "device_id": self.config.device_id,
                "name": self.config.device_name,
                "os": self.config.os_name,
            },
        )
        if reg_res.status_code == 201:
            dev = reg_res.json().get("data", {})
            self.device_uuid = dev.get("id")
            logger.info(f"Device enrolled successfully: {self.device_uuid}")
            return self.device_uuid
        else:
            raise RuntimeError(f"Failed to register device: {reg_res.text}")

    def upload_file_version(
        self,
        file_path: str,
        content_bytes: bytes,
        protected_folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload raw file content to server which compresses, encrypts with AES-256-GCM, and archives in MinIO."""
        if not self.device_uuid:
            self.enroll_or_get_device()

        b64_content = base64.b64encode(content_bytes).decode("utf-8")
        payload = {
            "device_id": self.device_uuid,
            "file_path": file_path,
            "file_content_base64": b64_content,
            "protected_folder_id": protected_folder_id,
        }

        res = self.request_with_retry(
            method="POST",
            path="backups/manual",
            json_data=payload,
        )
        if res.status_code in (200, 201):
            return res.json().get("data", {})
        else:
            raise RuntimeError(f"Failed to upload backup for {file_path}: {res.text}")

    def send_telemetry(
        self,
        file_path: str,
        content_bytes: Optional[bytes] = None,
        event_type: str = "FILE_MODIFY",
        old_path: Optional[str] = None,
        pid: Optional[int] = None,
        process_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send live telemetry to server detection engine before creating backup snapshot."""
        if not self.device_uuid:
            self.enroll_or_get_device()

        b64_content = None
        if content_bytes:
            b64_content = base64.b64encode(content_bytes[:65536]).decode("utf-8")

        payload = {
            "device_id": self.device_uuid,
            "file_path": file_path,
            "event_type": event_type,
            "content_base64": b64_content,
            "old_path": old_path,
            "pid": pid,
            "process_name": process_name,
        }

        res = self.request_with_retry(
            method="POST",
            path="threats/telemetry",
            json_data=payload,
        )
        if res.status_code in (200, 201):
            return res.json().get("data", {})
        return {}

