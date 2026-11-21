import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
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
        audit_entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            organization_id=organization_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit_entry)
        await self.db.flush()
        await self.db.refresh(audit_entry)
        return audit_entry

    async def list_logs(
        self,
        organization_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[AuditLog], int]:
        total_query = select(func.count()).select_from(AuditLog)
        query = select(AuditLog).order_by(AuditLog.created_at.desc())

        if organization_id:
            total_query = total_query.where(AuditLog.organization_id == organization_id)
            query = query.where(AuditLog.organization_id == organization_id)
        if user_id:
            total_query = total_query.where(AuditLog.user_id == user_id)
            query = query.where(AuditLog.user_id == user_id)
        if action:
            total_query = total_query.where(AuditLog.action == action)
            query = query.where(AuditLog.action == action)

        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

