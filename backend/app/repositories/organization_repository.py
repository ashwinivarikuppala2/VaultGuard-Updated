import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.organization import Organization
from app.repositories.base import BaseRepository
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationRepository(BaseRepository[Organization, OrganizationCreate, OrganizationUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(Organization, db)

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        query = select(Organization).where(Organization.slug == slug)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Organization]:
        query = select(Organization).where(func.lower(Organization.name) == func.lower(name))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_invite_code(self, invite_code: str) -> Optional[Organization]:
        query = select(Organization).where(func.upper(Organization.invite_code) == func.upper(invite_code.strip()))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_paginated(self, skip: int = 0, limit: int = 50) -> tuple[List[Organization], int]:
        total_query = select(func.count()).select_from(Organization)
        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one() or 0

        query = select(Organization).order_by(Organization.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

