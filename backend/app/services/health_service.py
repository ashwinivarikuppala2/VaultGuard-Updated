import time
from datetime import datetime, timezone
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.health import ServiceComponentHealth, SystemHealthResponse
from app.storage.minio_client import minio_storage


class HealthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_database(self) -> ServiceComponentHealth:
        start = time.perf_counter()
        try:
            await self.db.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000
            return ServiceComponentHealth(
                status="HEALTHY",
                latency_ms=round(latency, 2),
                details="PostgreSQL query OK",
            )
        except Exception as e:
            return ServiceComponentHealth(
                status="UNHEALTHY",
                latency_ms=None,
                details=f"PostgreSQL connection error: {str(e)}",
            )

    async def check_redis(self) -> ServiceComponentHealth:
        start = time.perf_counter()
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                socket_timeout=2.0,
                encoding="utf-8",
                decode_responses=True,
            )
            pong = await client.ping()
            latency = (time.perf_counter() - start) * 1000
            await client.aclose()
            if pong:
                return ServiceComponentHealth(
                    status="HEALTHY",
                    latency_ms=round(latency, 2),
                    details="Redis PING OK",
                )
            return ServiceComponentHealth(status="DEGRADED", details="Unexpected PING response")
        except Exception as e:
            return ServiceComponentHealth(
                status="UNHEALTHY",
                latency_ms=None,
                details=f"Redis connection error: {str(e)}",
            )

    async def check_minio(self) -> ServiceComponentHealth:
        start = time.perf_counter()
        is_healthy, details = minio_storage.check_health()
        latency = (time.perf_counter() - start) * 1000
        return ServiceComponentHealth(
            status="HEALTHY" if is_healthy else "UNHEALTHY",
            latency_ms=round(latency, 2) if is_healthy else None,
            details=details,
        )

    async def get_system_health(self) -> SystemHealthResponse:
        db_health = await self.check_database()
        redis_health = await self.check_redis()
        minio_health = await self.check_minio()

        services = {
            "database": db_health,
            "redis": redis_health,
            "minio": minio_health,
        }

        statuses = [s.status for s in services.values()]
        if all(s == "HEALTHY" for s in statuses):
            overall_status = "HEALTHY"
        elif any(s == "UNHEALTHY" for s in statuses):
            overall_status = "DEGRADED"
        else:
            overall_status = "HEALTHY"

        return SystemHealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
            environment=settings.ENVIRONMENT,
            services=services,
        )

