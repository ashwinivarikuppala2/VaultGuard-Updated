import logging
import os
from pathlib import Path, PurePosixPath
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
from app.core.exceptions import StorageUnavailableException

logger = logging.getLogger("vaultguard.storage")


class MinIOClient:
    def __init__(self) -> None:
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ROOT_USER
        self.secret_key = settings.MINIO_ROOT_PASSWORD
        self.secure = settings.MINIO_SECURE
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._client: Optional[Minio] = None

    def _local_object_path(self, root: Path, clean_path: str) -> Path:
        relative = PurePosixPath(clean_path.replace("\\", "/"))
        if relative.is_absolute() or not relative.parts or any(part in (".", "..") for part in relative.parts):
            raise ValueError("Invalid local storage object path.")

        bucket_root = (root.expanduser().resolve() / self.bucket_name).resolve()
        target = bucket_root.joinpath(*relative.parts).resolve()
        if bucket_root not in target.parents:
            raise ValueError("Local storage object path escapes its configured root.")
        return target

    def _local_roots(self) -> list[Path]:
        backend_dir = Path(__file__).resolve().parents[2]
        roots = [
            Path(settings.LOCAL_STORAGE_PATH),
            Path.cwd() / "local_storage",
            backend_dir / "local_storage",
            backend_dir.parent / "local_storage",
        ]
        unique_roots = []
        seen = set()
        for root in roots:
            resolved = root.expanduser().resolve()
            if resolved not in seen:
                unique_roots.append(resolved)
                seen.add(resolved)
        return unique_roots

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
        """Store encrypted data in MinIO or explicitly enabled local demo storage."""
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
            except Exception as exc:
                if not settings.LOCAL_STORAGE_ENABLED:
                    raise StorageUnavailableException(
                        "MinIO upload failed and local demo storage is disabled."
                    ) from exc
                logger.warning("MinIO upload failed; using explicitly enabled local demo storage.")
        elif not settings.LOCAL_STORAGE_ENABLED:
            raise StorageUnavailableException(
                "MinIO is unavailable and local demo storage is disabled."
            )

        local_file = self._local_object_path(Path(settings.LOCAL_STORAGE_PATH), clean_path)
        local_file.parent.mkdir(parents=True, exist_ok=True)
        with local_file.open("wb") as f:
            f.write(data)
        logger.info("Persisted %s bytes to local demo storage.", len(data))
        return f"{self.bucket_name}/{clean_path}"

    def download_bytes(self, object_path: str) -> bytes:
        """Retrieve encrypted data from MinIO or explicitly enabled local demo storage."""
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
            except Exception as exc:
                if not settings.LOCAL_STORAGE_ENABLED:
                    raise StorageUnavailableException(
                        "MinIO download failed and local demo storage is disabled."
                    ) from exc
                logger.warning("MinIO download failed; checking explicitly enabled local demo storage.")
        elif not settings.LOCAL_STORAGE_ENABLED:
            raise StorageUnavailableException(
                "MinIO is unavailable and local demo storage is disabled."
            )

        for root in self._local_roots():
            candidate = self._local_object_path(root, clean_path)
            if candidate.is_file():
                with candidate.open("rb") as f:
                    return f.read()

        raise FileNotFoundError(f"MinIO object missing: '{object_path}' not found in MinIO or local fallback storage.")


minio_storage = MinIOClient()

