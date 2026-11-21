import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthorizationException,
    DuplicateEntityException,
    EntityNotFoundException,
)
from app.models.protected_folder import ProtectedFolder
from app.models.role import RoleType
from app.models.user import User
from app.repositories.device_repository import DeviceRepository
from app.repositories.protected_folder_repository import ProtectedFolderRepository
from app.schemas.protected_folder import (
    ProtectedFolderCreate,
    ProtectedFolderResponse,
    ProtectedFolderUpdate,
)
from app.services.audit_service import AuditService


class ProtectedFolderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ProtectedFolderRepository(db)
        self.device_repo = DeviceRepository(db)
        self.audit_service = AuditService(db)

    async def create_protected_folder(
        self,
        folder_in: ProtectedFolderCreate,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ProtectedFolderResponse:
        device = await self.device_repo.get_by_id(folder_in.device_id)
        if not device:
            raise EntityNotFoundException("Device", folder_in.device_id)

        # RBAC Check: Ensure user owns device or admin belongs to same organization
        if current_user.role.name in [RoleType.EMPLOYEE.value, RoleType.INDIVIDUAL.value]:
            if (
                device.user_id != current_user.id
                or device.organization_id != current_user.organization_id
            ):
                raise AuthorizationException("Access denied: You can only configure protected folders on your own devices.")
        elif current_user.role.name == RoleType.ADMIN.value:
            if (
                device.organization_id != current_user.organization_id
                or device.user_id != current_user.id
            ):
                raise AuthorizationException("Protected folders may only be changed on your own devices.")
        else:
            raise AuthorizationException("Protected folders may only be changed on your own devices.")

        # Check duplicate folder path on same device
        existing = await self.repository.get_by_path(folder_in.device_id, folder_in.folder_path)
        if existing:
            raise DuplicateEntityException("ProtectedFolder", "folder_path", folder_in.folder_path)

        folder = ProtectedFolder(
            organization_id=device.organization_id,
            device_id=folder_in.device_id,
            folder_path=folder_in.folder_path,
            scan_interval_seconds=folder_in.scan_interval_seconds,
            include_patterns=folder_in.include_patterns,
            exclude_patterns=folder_in.exclude_patterns,
            is_active=folder_in.is_active,
        )
        self.db.add(folder)
        await self.db.flush()
        await self.db.refresh(folder)

        await self.audit_service.log(
            action="PROTECTED_FOLDER_CREATED",
            resource_type="ProtectedFolder",
            resource_id=str(folder.id),
            organization_id=device.organization_id,
            user_id=current_user.id,
            details={"folder_path": folder.folder_path, "device_id": str(device.id)},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return ProtectedFolderResponse.model_validate(folder)

    async def list_protected_folders(
        self,
        current_user: User,
        device_id: Optional[uuid.UUID] = None,
    ) -> List[ProtectedFolderResponse]:
        if current_user.role.name in [RoleType.EMPLOYEE.value, RoleType.INDIVIDUAL.value]:
            if device_id:
                dev = await self.device_repo.get_by_id(device_id)
                if (
                    not dev
                    or dev.user_id != current_user.id
                    or dev.organization_id != current_user.organization_id
                ):
                    return []
                folders = await self.repository.list_by_device(device_id=device_id)
                return [ProtectedFolderResponse.model_validate(f) for f in folders]
            else:
                all_folders = []
                device_ids = await self.device_repo.list_ids_by_user(
                    current_user.id, current_user.organization_id
                )
                for owned_device_id in device_ids:
                    folders = await self.repository.list_by_device(device_id=owned_device_id)
                    all_folders.extend(folders)
                return [ProtectedFolderResponse.model_validate(f) for f in all_folders]

        if current_user.role.name != RoleType.ADMIN.value:
            return []

        device_ids = await self.device_repo.list_ids_by_user(
            current_user.id, current_user.organization_id
        )
        if current_user.organization_id:
            employee_ids = await self.device_repo.list_employee_ids_by_organization(
                current_user.organization_id
            )
            device_ids = list(dict.fromkeys([*device_ids, *employee_ids]))
        if device_id:
            if device_id not in device_ids:
                return []
            folders = await self.repository.list_by_device(device_id=device_id)
            return [ProtectedFolderResponse.model_validate(f) for f in folders]

        all_folders = []
        for visible_device_id in device_ids:
            all_folders.extend(
                await self.repository.list_by_device(device_id=visible_device_id)
            )
        return [ProtectedFolderResponse.model_validate(f) for f in all_folders]

    async def delete_protected_folder(
        self,
        folder_id: uuid.UUID,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        folder = await self.repository.get_by_id(folder_id)
        if not folder:
            raise EntityNotFoundException("ProtectedFolder", folder_id)

        device = await self.device_repo.get_by_id(folder.device_id)
        if current_user.role.name in [RoleType.EMPLOYEE.value, RoleType.INDIVIDUAL.value]:
            if (
                not device
                or device.user_id != current_user.id
                or device.organization_id != current_user.organization_id
            ):
                raise AuthorizationException("Access denied: You can only remove protected folders from your own devices.")
        elif current_user.role.name == RoleType.ADMIN.value:
            if (
                not device
                or folder.organization_id != current_user.organization_id
                or device.user_id != current_user.id
            ):
                raise AuthorizationException("Protected folders may only be changed on your own devices.")
        else:
            raise AuthorizationException("Protected folders may only be changed on your own devices.")

        await self.repository.delete(folder)

        await self.audit_service.log(
            action="PROTECTED_FOLDER_DELETED",
            resource_type="ProtectedFolder",
            resource_id=str(folder_id),
            organization_id=folder.organization_id,
            user_id=current_user.id,
            details={"deleted_folder_path": folder.folder_path},
            ip_address=ip_address,
            user_agent=user_agent,
        )

