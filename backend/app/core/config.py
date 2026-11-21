from typing import List, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
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
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @model_validator(mode="after")
    def _reject_default_secret_outside_development(self):
        # The published default key is only acceptable for local development and tests.
        if self.ENVIRONMENT.lower() not in ("development", "test") and self.SECRET_KEY == _DEFAULT_SECRET_KEY:
            raise ValueError("SECRET_KEY must be set to a unique value when ENVIRONMENT is not development or test.")
        return self

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

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
    FIRST_SUPER_ADMIN_PASSWORD: str = "AdminSecurePassword123!"
    FIRST_SUPER_ADMIN_NAME: str = "System Super Administrator"


settings = Settings()

