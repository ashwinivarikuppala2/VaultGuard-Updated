import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.role import Role, RoleType
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_id(self, id: uuid.UUID) -> Optional[User]:
        query = (
            select(User)
            .options(selectinload(User.role), selectinload(User.organization))
            .where(User.id == id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        query = (
            select(User)
            .options(selectinload(User.role), selectinload(User.organization))
            .where(func.lower(User.email) == func.lower(email))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_role_by_type(self, role_type: RoleType) -> Optional[Role]:
        query = select(Role).where(Role.name == role_type.value)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[List[User], int]:
        total_query = select(func.count()).select_from(User).where(User.organization_id == organization_id)
        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one() or 0

        query = (
            select(User)
            .options(selectinload(User.role), selectinload(User.organization))
            .where(User.organization_id == organization_id)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

