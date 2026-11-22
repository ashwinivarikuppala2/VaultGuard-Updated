import json
from typing import List, Optional, Union
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_SECRET_KEY = "vaultguard-super-secure-production-grade-secret-key-change-me-32-chars-min"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Environment
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "VaultGuard - Anti-Ransomware Backup System"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://vaultguard-5vs4.onrender.com",
    ]

    @model_validator(mode="after")
    def _normalize_cors_origins(self):
        value = self.BACKEND_CORS_ORIGINS
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    value = parsed if isinstance(parsed, list) else []
                except json.JSONDecodeError:
                    value = []
            else:
                value = [item.strip() for item in value.split(",") if item.strip()]
        if not isinstance(value, list):
            value = []
        self.BACKEND_CORS_ORIGINS = list(
            dict.fromkeys(str(item).strip().rstrip("/") for item in value if str(item).strip())
        )
        return self

    @model_validator(mode="after")
    def _reject_default_secret_outside_development(self):
        # The published default key is only acceptable for local development and tests.
        if self.ENVIRONMENT.lower() not in ("development", "test") and self.SECRET_KEY == _DEFAULT_SECRET_KEY:
            raise ValueError("SECRET_KEY must be set to a unique value when ENVIRONMENT is not development or test.")
        return self

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            value = v.strip()
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        v = parsed
                    else:
                        v = []
                except json.JSONDecodeError:
                    v = []
            else:
                v = [item.strip() for item in value.split(",") if item.strip()]

        if not isinstance(v, list):
            return []
        return list(dict.fromkeys(str(item).strip().rstrip("/") for item in v if str(item).strip()))

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            return v
        url = v.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]

        if url.startswith("postgresql+asyncpg://"):
            parsed = urlsplit(url)
            query = [
                (key, value)
                for key, value in parse_qsl(parsed.query, keep_blank_values=True)
                if key.lower() not in ("sslmode", "ssl")
            ]
            url = urlunsplit(
                (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
            )
        return url

    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "vaultguard_db"
    POSTGRES_USER: str = "vaultguard_user"
    POSTGRES_PASSWORD: str = "vaultguard_secure_password"
    DATABASE_URL: str ="sqlite+aiosqlite:///./vaultguard.db"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = "redis://redis:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadminpassword"
    MINIO_BUCKET_NAME: str = "vaultguard-storage"
    MINIO_SECURE: bool = False
    LOCAL_STORAGE_ENABLED: Optional[bool] = None
    LOCAL_STORAGE_PATH: str = "local_storage"

    # ClamAV daemon connection used by the mandatory pre-backup scanner.
    CLAMAV_HOST: str = "clamav"
    CLAMAV_PORT: int = 3310
    CLAMAV_TIMEOUT_SECONDS: int = 300

    # Upload limits
    # Maximum single-file upload size in megabytes.
    # Must be consistent with Nginx client_max_body_size (500m).
    MAX_UPLOAD_SIZE_MB: int = 500

    # Seed Admin
    FIRST_SUPER_ADMIN_EMAIL: str = "admin@vaultguard.internal"
    FIRST_SUPER_ADMIN_PASSWORD: Optional[str] = None
    FIRST_SUPER_ADMIN_NAME: str = "System Super Administrator"

    @model_validator(mode="after")
    def _set_local_storage_default(self):
        if self.LOCAL_STORAGE_ENABLED is None:
            self.LOCAL_STORAGE_ENABLED = self.ENVIRONMENT.lower() in ("development", "test")
        return self


settings = Settings()

