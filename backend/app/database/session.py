import logging
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.models.base import Base
from app.core.config import settings

logger = logging.getLogger("vaultguard.database")

db_url = settings.DATABASE_URL
is_in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER") == "true"

# If running outside Docker and DATABASE_URL points to the container host 'postgres', fall back to local SQLite
if not is_in_docker and ("@postgres:" in db_url or "postgres@" in db_url):
    db_url = "sqlite+aiosqlite:///./vaultguard.db"
    logger.info("[DATABASE] Local host environment detected (non-docker). Using SQLite: ./vaultguard.db")

# Async Engine configuration (Adaptive for PostgreSQL and SQLite)
engine_kwargs = {"echo": settings.DEBUG}
if "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 20,
        "max_overflow": 10,
    })

engine = create_async_engine(db_url, **engine_kwargs)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base imported from app.models.base


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection yield for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

