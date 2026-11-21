import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthorizationException,
    DuplicateEntityException,
    EntityNotFoundException,
    VaultGuardException,
)
from app.models.device import Device, DeviceStatus
from app.models.role import RoleType
from app.models.user import User
from app.repositories.device_repository import DeviceRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.device import DeviceCreate, DeviceResponse, DeviceUpdate
from app.services.audit_service import AuditService


class DeviceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DeviceRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.audit_service = AuditService(db)

    async def register_device(
        self,
        device_in: DeviceCreate,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> DeviceResponse:
        # Check existing device_id
        existing = await self.repository.get_by_device_id(device_in.device_id)
        if existing:
            raise DuplicateEntityException("Device", "device_id", device_in.device_id)

        target_org_id = None
        if current_user.role.name == RoleType.INDIVIDUAL.value:
            # Personal user - no organization
            target_org_id = None
        else:
            # Organization user (ADMIN or EMPLOYEE)
            target_org_id = current_user.organization_id
            if not target_org_id:
                raise AuthorizationException("Current user is not associated with an organization.")

            org = await self.org_repo.get_by_id(target_org_id)
            if not org:
                raise EntityNotFoundException("Organization", target_org_id)

            # Check max devices limit for organization
            _, current_count = await self.repository.list_by_organization(organization_id=target_org_id)
            if current_count >= org.max_devices:
                raise VaultGuardException(
                    f"Organization device limit reached ({org.max_devices} devices max)."
                )

        new_device = Device(
            device_id=device_in.device_id,
            name=device_in.name,
            os=device_in.os,
            status=DeviceStatus.ONLINE,
            last_seen=datetime.now(timezone.utc),
            organization_id=target_org_id,
            user_id=current_user.id,
        )
        self.db.add(new_device)
        await self.db.flush()
        await self.db.refresh(new_device)

        # Log audit entry
        await self.audit_service.log(
            action="DEVICE_REGISTERED",
            resource_type="Device",
            resource_id=new_device.device_id,
            organization_id=target_org_id,
            user_id=current_user.id,
            details={"device_id": new_device.device_id, "os": new_device.os, "name": new_device.name},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return DeviceResponse.model_validate(new_device)

    async def list_devices(
        self,
        current_user: User,
        status: Optional[DeviceStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[DeviceResponse], int]:
        if current_user.role.name in [RoleType.INDIVIDUAL.value, RoleType.EMPLOYEE.value]:
            devices, total = await self.repository.list_by_user(
                user_id=current_user.id,
                status=status,
                skip=skip,
                limit=limit,
                organization_id=current_user.organization_id,
                strict_organization=True,
            )
            return [DeviceResponse.model_validate(d) for d in devices], total

        if current_user.role.name != RoleType.ADMIN.value:
            return [], 0

        if not current_user.organization_id:
            return [], 0

        visible_ids = await self.repository.list_ids_by_user(
            current_user.id, current_user.organization_id
        )
        visible_ids.extend(
            await self.repository.list_employee_ids_by_organization(
                current_user.organization_id
            )
        )
        devices, total = await self.repository.list_by_ids(
            device_ids=list(dict.fromkeys(visible_ids)),
            status=status,
            skip=skip,
            limit=limit,
        )
        return [DeviceResponse.model_validate(d) for d in devices], total

    async def get_device(
        self,
        device_id: str,
        current_user: User,
    ) -> DeviceResponse:
        device = await self.repository.get_by_device_id(device_id)
        if not device:
            raise EntityNotFoundException("Device", device_id)

        if current_user.role.name in [RoleType.INDIVIDUAL.value, RoleType.EMPLOYEE.value]:
            if (
                device.user_id != current_user.id
                or device.organization_id != current_user.organization_id
            ):
                raise AuthorizationException("Access denied to this device.")
        elif current_user.role.name == RoleType.ADMIN.value:
            is_own_device = (
                device.organization_id == current_user.organization_id
                and device.user_id == current_user.id
            )
            is_employee_device = (
                current_user.organization_id is not None
                and await self.repository.is_employee_owned_device(
                    device.id, current_user.organization_id
                )
            )
            if not is_own_device and not is_employee_device:
                raise AuthorizationException("Access denied to this device.")
        else:
            raise AuthorizationException("Access denied to this device.")

        return DeviceResponse.model_validate(device)

    async def update_device(
        self,
        device_id: str,
        device_in: DeviceUpdate,
        current_user: User,
    ) -> DeviceResponse:
        device = await self.repository.get_by_device_id(device_id)
        if not device:
            raise EntityNotFoundException("Device", device_id)

        if current_user.role.name in [RoleType.INDIVIDUAL.value, RoleType.EMPLOYEE.value]:
            if (
                device.user_id != current_user.id
                or device.organization_id != current_user.organization_id
            ):
                raise AuthorizationException("Access denied to update this device.")
        elif current_user.role.name == RoleType.ADMIN.value:
            if (
                device.organization_id != current_user.organization_id
                or device.user_id != current_user.id
            ):
                raise AuthorizationException("Access denied to update this device.")
        else:
            raise AuthorizationException("Access denied to update this device.")

        update_dict = device_in.model_dump(exclude_unset=True)
        updated = await self.repository.update(device, update_dict)
        return DeviceResponse.model_validate(updated)

