import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, success_response
from app.database.session import get_db
from app.models.role import RoleType
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse
from app.schemas.common import PaginatedResponse
from app.security.rbac import get_current_user, require_roles
from app.services.audit_service import AuditService

router = APIRouter()


@router.get(
    "",
    response_model=ApiResponse[PaginatedResponse[AuditLogResponse]],
    dependencies=[Depends(require_roles([RoleType.ADMIN, RoleType.INDIVIDUAL]))],
)
async def list_audit_logs(
    request: Request,
    organization_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[AuditLogResponse]]:
    audit_service = AuditService(db)

    # Scoping: force org_id to current user's org
    effective_org_id = current_user.organization_id

    logs, total = await audit_service.get_recent_logs(
        organization_id=effective_org_id,
        user_id=user_id,
        action=action,
        skip=skip,
        limit=limit,
    )
    items = [AuditLogResponse.model_validate(l) for l in logs]
    trace_id = getattr(request.state, "trace_id", None)
    data = PaginatedResponse[AuditLogResponse](
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )
    return success_response(data=data.model_dump(), trace_id=trace_id)

