import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.device import Device, DeviceStatus
from app.models.role import Role
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.device import DeviceCreate, DeviceUpdate


class DeviceRepository(BaseRepository[Device, DeviceCreate, DeviceUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(Device, db)

    async def get_by_device_id(self, device_id: str) -> Optional[Device]:
        query = select(Device).where(Device.device_id == device_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: Optional[uuid.UUID] = None,
        status: Optional[DeviceStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Device], int]:
        total_query = select(func.count()).select_from(Device)
        query = select(Device).order_by(Device.created_at.desc())

        if organization_id:
            total_query = total_query.where(Device.organization_id == organization_id)
            query = query.where(Device.organization_id == organization_id)
        if status:
            total_query = total_query.where(Device.status == status)
            query = query.where(Device.status == status)

        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[DeviceStatus] = None,
        skip: int = 0,
        limit: int = 50,
        organization_id: Optional[uuid.UUID] = None,
        strict_organization: bool = False,
    ) -> tuple[List[Device], int]:
        total_query = select(func.count()).select_from(Device).where(Device.user_id == user_id)
        query = select(Device).where(Device.user_id == user_id).order_by(Device.created_at.desc())
        if strict_organization:
            total_query = total_query.where(Device.organization_id == organization_id)
            query = query.where(Device.organization_id == organization_id)
        elif organization_id is not None:
            total_query = total_query.where(Device.organization_id == organization_id)
            query = query.where(Device.organization_id == organization_id)

        if status:
            total_query = total_query.where(Device.status == status)
            query = query.where(Device.status == status)

        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def list_ids_by_user(
        self,
        user_id: uuid.UUID,
        organization_id: Optional[uuid.UUID] = None,
    ) -> List[uuid.UUID]:
        query = select(Device.id).where(
            Device.user_id == user_id,
            Device.organization_id == organization_id,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_employee_ids_by_organization(
        self,
        organization_id: uuid.UUID,
    ) -> List[uuid.UUID]:
        query = (
            select(Device.id)
            .join(User, Device.user_id == User.id)
            .join(Role, User.role_id == Role.id)
            .where(
                Device.organization_id == organization_id,
                Role.name == "EMPLOYEE",
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_by_ids(
        self,
        device_ids: List[uuid.UUID],
        status: Optional[DeviceStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Device], int]:
        total_query = select(func.count()).select_from(Device).where(Device.id.in_(device_ids))
        query = select(Device).where(Device.id.in_(device_ids)).order_by(Device.created_at.desc())
        if status:
            total_query = total_query.where(Device.status == status)
            query = query.where(Device.status == status)

        total_result = await self.db.execute(total_query)
        total = total_result.scalar_one() or 0
        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def is_employee_owned_device(
        self,
        device_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> bool:
        query = (
            select(Device.id)
            .join(User, Device.user_id == User.id)
            .join(Role, User.role_id == Role.id)
            .where(
                Device.id == device_id,
                Device.organization_id == organization_id,
                Role.name == "EMPLOYEE",
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

