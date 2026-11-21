import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, db: AsyncSession):
        self.repository = AuditRepository(db)

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        organization_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        return await self.repository.log_event(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            organization_id=organization_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def get_recent_logs(
        self,
        organization_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[AuditLog], int]:
        return await self.repository.list_logs(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            skip=skip,
            limit=limit,
        )

