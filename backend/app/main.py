import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.responses import success_response
from app.database.session import AsyncSessionLocal, engine
from app.middleware.error_handler import register_exception_handlers
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.models.base import Base
from app.models.device import Device, DeviceStatus
from app.models.role import Role, RoleType
from app.models.user import User
from app.security.password import hash_password
from app.storage.minio_client import minio_storage

# Configure structured root logger
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
)
logger = logging.getLogger("vaultguard.main")


async def init_system_defaults() -> None:
    """Idempotently seed essential database records (Roles, Super Admin)."""
    async with AsyncSessionLocal() as session:
        try:
            # 1. Seed Roles
            for role_type in RoleType:
                query = select(Role).where(Role.name == role_type.value)
                result = await session.execute(query)
                if not result.scalar_one_or_none():
                    role = Role(
                        name=role_type.value,
                        description=f"Standard system role for {role_type.value}",
                    )
                    session.add(role)
            await session.commit()

            # 2. Seed Default Administrator
            admin_role_res = await session.execute(
                select(Role).where(Role.name == RoleType.ADMIN.value)
            )
            admin_role = admin_role_res.scalar_one()

            admin_query = select(User).where(User.email == settings.FIRST_SUPER_ADMIN_EMAIL)
            admin_result = await session.execute(admin_query)
            admin_user = admin_result.scalar_one_or_none()

            if not admin_user:
                admin_user = User(
                    email=settings.FIRST_SUPER_ADMIN_EMAIL,
                    hashed_password=hash_password(settings.FIRST_SUPER_ADMIN_PASSWORD),
                    full_name=settings.FIRST_SUPER_ADMIN_NAME,
                    organization_id=None,
                    role_id=admin_role.id,
                    is_active=True,
                    is_verified=True,
                )
                session.add(admin_user)
                await session.commit()
                logger.info(f"System Administrator seeded: {settings.FIRST_SUPER_ADMIN_EMAIL}")
            else:
                logger.info("System Administrator already provisioned.")

            # 3. Seed Default Threat Rules (Module 3)
            from app.models.threat import ThreatRule
            rules_res = await session.execute(select(func.count(ThreatRule.id)))
            if (rules_res.scalar() or 0) == 0:
                default_rules = [
                    ThreatRule(
                        name="High Shannon Entropy",
                        description="Flags ciphertext buffers exceeding 7.5 Shannon entropy",
                        rule_type="ENTROPY",
                        condition="GREATER_THAN",
                        threshold=7.5,
                        weight=35.0,
                        severity="HIGH",
                        action="ALERT",
                    ),
                    ThreatRule(
                        name="Mass File Renaming Burst",
                        description="Triggers when rename rate exceeds 25 files per minute",
                        rule_type="RENAME_RATE",
                        condition="GREATER_THAN",
                        threshold=25.0,
                        weight=30.0,
                        severity="HIGH",
                        action="QUARANTINE",
                    ),
                    ThreatRule(
                        name="Rapid Write Frequency Spike",
                        description="Triggers when write rate exceeds 60 modifications per minute",
                        rule_type="WRITE_RATE",
                        condition="GREATER_THAN",
                        threshold=60.0,
                        weight=25.0,
                        severity="HIGH",
                        action="ALERT",
                    ),
                    ThreatRule(
                        name="Canary Decoy Tampering Tripwire",
                        description="Instant critical alert and host isolation when decoy files are touched",
                        rule_type="CANARY",
                        condition="EQUALS",
                        threshold=1.0,
                        weight=85.0,
                        severity="CRITICAL",
                        action="QUARANTINE",
                    ),
                ]
                session.add_all(default_rules)
                await session.commit()
                logger.info("Default Threat Detection Heuristic Rules seeded.")

            # // TEMP TEST DEVICE
            sample_user_result = await session.execute(
                select(User)
                .where(User.organization_id.is_not(None))
                .order_by(User.last_login_at.desc().nullslast())
                .limit(1)
            )
            sample_user = sample_user_result.scalar_one_or_none()
            if sample_user and sample_user.organization_id:
                device_count_result = await session.execute(
                    select(func.count(Device.id)).where(
                        Device.organization_id == sample_user.organization_id
                    )
                )
                if (device_count_result.scalar() or 0) == 0:
                    session.add(
                        Device(
                            device_id=str(uuid.uuid4()),
                            name="My Windows PC",
                            os="Windows",
                            status=DeviceStatus.ONLINE,
                            organization_id=sample_user.organization_id,
                            user_id=sample_user.id,
                        )
                    )
                    await session.commit()
                    logger.info("Temporary test device seeded for the most recently active organization.")
            # // REMOVE BEFORE PRODUCTION
        except Exception as e:
            await session.rollback()
            logger.error(f"Error during system seeding: {str(e)}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Initializing VaultGuard platform services...")

    # NOTE: Table creation is handled exclusively by Alembic migrations
    # (alembic upgrade head runs before uvicorn in docker-compose).
    # Base.metadata.create_all is intentionally NOT called here to prevent
    # it from creating tables that Alembic should own, which would cause
    # "relation already exists" errors on the next migration run.
    # In development without Docker, run: alembic upgrade head

    # Initialize MinIO Storage Bucket
    minio_storage.initialize_bucket()

    # Seed system roles & super administrator
    await init_system_defaults()

    logger.info("VaultGuard Platform core initialized successfully.")
    yield
    logger.info("Shutting down VaultGuard platform services...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Secure Cloud Backup & Recovery System Against Ransomware - Module 1: Foundation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 1. Centralized exception handling
register_exception_handlers(app)

# 2. Custom Request Logging & Correlation ID Middleware
app.add_middleware(RequestLoggingMiddleware)

# 3. CORS Guard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Mount API v1 Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root_index():
    return success_response(
        data={
            "service": settings.PROJECT_NAME,
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "status": "OPERATIONAL",
            "docs": "/docs",
        }
    )

