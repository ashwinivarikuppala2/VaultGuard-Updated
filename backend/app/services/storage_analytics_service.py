from sqlalchemy.ext.asyncio import AsyncSession
from app.models.role import RoleType
from app.models.user import User
from app.repositories.backup_repository import BackupRepository
from app.repositories.device_repository import DeviceRepository
from app.schemas.storage import DeviceStorageUsage, StorageStatisticsResponse


class StorageAnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = BackupRepository(db)

    async def get_statistics(self, current_user: User) -> StorageStatisticsResponse:
        if current_user.role.name == RoleType.ADMIN.value:
            device_repository = DeviceRepository(self.db)
            device_ids = await device_repository.list_ids_by_user(
                current_user.id, current_user.organization_id
            )
            if current_user.organization_id:
                employee_ids = await device_repository.list_employee_ids_by_organization(
                    current_user.organization_id
                )
                device_ids = list(dict.fromkeys([*device_ids, *employee_ids]))
            stats_dict = await self.repository.get_storage_statistics(device_ids=device_ids)
        elif current_user.role.name in [RoleType.INDIVIDUAL.value, RoleType.EMPLOYEE.value]:
            device_ids = await DeviceRepository(self.db).list_ids_by_user(
                current_user.id, current_user.organization_id
            )
            stats_dict = await self.repository.get_storage_statistics(device_ids=device_ids)
        else:
            stats_dict = await self.repository.get_storage_statistics(device_ids=[])

        device_breakdown = [
            DeviceStorageUsage(**d) for d in stats_dict.pop("device_breakdown", [])
        ]

        return StorageStatisticsResponse(
            **stats_dict,
            device_breakdown=device_breakdown,
        )

