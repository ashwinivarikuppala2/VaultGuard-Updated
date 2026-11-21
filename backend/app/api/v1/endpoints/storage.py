from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.user import User
from app.schemas.storage import StorageStatisticsResponse
from app.security.rbac import get_current_user
from app.services.storage_analytics_service import StorageAnalyticsService

router = APIRouter()


@router.get("/statistics", response_model=ApiResponse[StorageStatisticsResponse])
async def get_storage_statistics(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[StorageStatisticsResponse]:
    """Retrieve global or organization-level storage metrics, savings, and volume stats."""
    service = StorageAnalyticsService(db)
    stats = await service.get_statistics(current_user=current_user)
    trace_id = getattr(request.state, "trace_id", None)
    return success_response(data=stats.model_dump(), trace_id=trace_id)

