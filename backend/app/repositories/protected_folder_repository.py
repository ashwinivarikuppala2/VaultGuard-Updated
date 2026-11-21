import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.protected_folder import ProtectedFolder
from app.repositories.base import BaseRepository
from app.schemas.protected_folder import ProtectedFolderCreate, ProtectedFolderUpdate


class ProtectedFolderRepository(BaseRepository[ProtectedFolder, ProtectedFolderCreate, ProtectedFolderUpdate]):
    def __init__(self, db: AsyncSession):
        super().__init__(ProtectedFolder, db)

    async def list_by_organization(
        self, organization_id: Optional[uuid.UUID] = None, device_id: Optional[uuid.UUID] = None
    ) -> List[ProtectedFolder]:
        query = select(ProtectedFolder)
        if organization_id is not None:
            query = query.where(ProtectedFolder.organization_id == organization_id)
        if device_id:
            query = query.where(ProtectedFolder.device_id == device_id)
        query = query.order_by(ProtectedFolder.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_by_device(self, device_id: uuid.UUID) -> List[ProtectedFolder]:
        query = select(ProtectedFolder).where(ProtectedFolder.device_id == device_id).order_by(ProtectedFolder.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_path(
        self, device_id: uuid.UUID, folder_path: str
    ) -> Optional[ProtectedFolder]:
        query = select(ProtectedFolder).where(
            ProtectedFolder.device_id == device_id,
            ProtectedFolder.folder_path == folder_path,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

