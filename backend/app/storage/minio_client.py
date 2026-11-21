import logging
import os
from typing import Optional, Tuple

try:
    from minio import Minio
    from minio.error import S3Error
    HAS_MINIO = True
except ImportError:
    Minio = None  # type: ignore
    S3Error = Exception  # type: ignore
    HAS_MINIO = False

from app.core.config import settings

logger = logging.getLogger("vaultguard.storage")


class MinIOClient:
    def __init__(self) -> None:
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ROOT_USER
        self.secret_key = settings.MINIO_ROOT_PASSWORD
        self.secure = settings.MINIO_SECURE
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._client: Optional[Minio] = None

    @property
    def is_available(self) -> bool:
        if not HAS_MINIO:
            return False
        if not hasattr(self, "_available_cached"):
            is_in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER") == "true"
            if not is_in_docker and (self.endpoint.startswith("minio:") or self.endpoint == "minio"):
                self._available_cached = False
                return False
            import socket
            try:
                host, port_str = self.endpoint.split(":") if ":" in self.endpoint else (self.endpoint, "9000")
                with socket.create_connection((host, int(port_str)), timeout=0.2):
                    self._available_cached = True
            except Exception:
                self._available_cached = False
        return self._available_cached

    @property
    def client(self) -> Optional[Minio]:
        if not self.is_available:
            return None
        if self._client is None and Minio:
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    def initialize_bucket(self) -> bool:
        """Verify connection and idempotently create the default bucket."""
        if not HAS_MINIO:
            logger.warning("MinIO package not installed. Object storage features will be mocked.")
            return False

        # Fast non-blocking check to prevent slow socket timeouts outside Docker
        is_in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER") == "true"
        if not is_in_docker and self.endpoint.startswith("minio:"):
            logger.info(f"MinIO storage container host '{self.endpoint}' not running locally. Continuing platform startup.")
            return False

        try:
            if self.client and not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"MinIO bucket '{self.bucket_name}' created successfully.")
            else:
                logger.info(f"MinIO bucket '{self.bucket_name}' ready.")
            return True
        except Exception as e:
            logger.warning(f"MinIO storage offline (continuing platform startup): {str(e)}")
            return False

    def check_health(self) -> Tuple[bool, Optional[str]]:
        """Probe MinIO service readiness."""
        if not HAS_MINIO:
            return False, "MinIO driver not installed (run 'pip install minio')"
        try:
            if not self.client:
                return False, "MinIO client not configured"
            exists = self.client.bucket_exists(self.bucket_name)
            return True, f"Bucket '{self.bucket_name}' accessible (exists={exists})"
        except S3Error as e:
            return False, f"MinIO S3 Error: {e.code} - {e.message}"
        except Exception as e:
            return False, f"MinIO Offline: {str(e)}"

    def upload_bytes(
        self,
        object_path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload encrypted payload to MinIO with local fallback for offline/development."""
        clean_path = object_path
        if clean_path.startswith(f"{self.bucket_name}/"):
            clean_path = clean_path[len(self.bucket_name) + 1:]

        import io
        if self.client:
            try:
                data_stream = io.BytesIO(data)
                self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=clean_path,
                    data=data_stream,
                    length=len(data),
                    content_type=content_type,
                )
                logger.info(f"Uploaded {len(data)} bytes to MinIO: '{self.bucket_name}/{clean_path}'")
                return f"{self.bucket_name}/{clean_path}"
            except Exception as e:
                logger.warning(f"MinIO upload error ({str(e)}), persisting to local storage fallback.")

        # Local storage fallback for standalone development / offline testing
        local_dir = os.path.join("local_storage", self.bucket_name, os.path.dirname(clean_path))
        os.makedirs(local_dir, exist_ok=True)
        local_file = os.path.join("local_storage", self.bucket_name, clean_path)
        with open(local_file, "wb") as f:
            f.write(data)
        logger.info(f"Persisted {len(data)} bytes to local storage: '{local_file}'")
        return f"{self.bucket_name}/{clean_path}"

    def download_bytes(self, object_path: str) -> bytes:
        """Download encrypted payload from MinIO or local fallback."""
        clean_path = object_path
        if clean_path.startswith(f"{self.bucket_name}/"):
            clean_path = clean_path[len(self.bucket_name) + 1:]

        if self.client:
            try:
                response = self.client.get_object(self.bucket_name, clean_path)
                data = response.read()
                response.close()
                response.release_conn()
                return data
            except Exception as e:
                logger.warning(f"MinIO get_object error ({str(e)}), checking local fallback.")

        # Check clean path in local fallback
        # Resolve the backend directory (parent of this file's package root)
        _backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _root_dir = os.path.dirname(_backend_dir) if os.path.basename(_backend_dir).lower() == "backend" else _backend_dir
        candidates = [
            os.path.join("local_storage", self.bucket_name, clean_path),
            os.path.join("local_storage", self.bucket_name, object_path),
            os.path.join(os.getcwd(), "local_storage", self.bucket_name, clean_path),
            os.path.join(_backend_dir, "local_storage", self.bucket_name, clean_path),
            os.path.join(_root_dir, "local_storage", self.bucket_name, clean_path),
        ]
        for candidate in candidates:
            if os.path.exists(candidate) and os.path.isfile(candidate):
                with open(candidate, "rb") as f:
                    return f.read()

        raise FileNotFoundError(f"MinIO object missing: '{object_path}' not found in MinIO or local fallback storage.")


minio_storage = MinIOClient()

