from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.user import User
from app.security.rbac import get_current_user
from app.schemas.health import ServiceComponentHealth, SystemHealthResponse
from app.services.health_service import HealthService

router = APIRouter()


@router.get("", response_model=ApiResponse[SystemHealthResponse])
async def get_system_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[SystemHealthResponse]:
    health_service = HealthService(db)
    result = await health_service.get_system_health()
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)


@router.get("/db", response_model=ApiResponse[ServiceComponentHealth])
async def get_db_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ServiceComponentHealth]:
    health_service = HealthService(db)
    result = await health_service.check_database()
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)


@router.get("/redis", response_model=ApiResponse[ServiceComponentHealth])
async def get_redis_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ServiceComponentHealth]:
    health_service = HealthService(db)
    result = await health_service.check_redis()
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)


@router.get("/minio", response_model=ApiResponse[ServiceComponentHealth])
async def get_minio_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ServiceComponentHealth]:
    health_service = HealthService(db)
    result = await health_service.check_minio()
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=result.model_dump(), trace_id=trace_id)

