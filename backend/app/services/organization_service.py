import re
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AuthorizationException,
    DuplicateEntityException,
    EntityNotFoundException,
)
from app.models.organization import Organization, generate_organization_invite_code
from app.models.role import RoleType
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.schemas.user import UserResponse
from app.services.audit_service import AuditService


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = OrganizationRepository(db)
        self.audit_service = AuditService(db)

    async def create_organization(
        self,
        org_in: OrganizationCreate,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> OrganizationResponse:
        # Check name uniqueness
        existing_name = await self.repository.get_by_name(org_in.name)
        if existing_name:
            raise DuplicateEntityException("Organization", "name", org_in.name)

        slug = org_in.slug
        if not slug:
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", org_in.name.lower()).strip("-")

        existing_slug = await self.repository.get_by_slug(slug)
        if existing_slug:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        invite_code = generate_organization_invite_code()
        new_org = Organization(
            name=org_in.name,
            slug=slug,
            contact_email=org_in.contact_email,
            invite_code=invite_code,
            max_devices=org_in.max_devices,
            storage_quota_bytes=org_in.storage_quota_bytes,
            is_active=True,
        )
        self.db.add(new_org)
        await self.db.flush()
        await self.db.refresh(new_org)
        if current_user.organization_id is None:
            current_user.organization_id = new_org.id

        # Log audit entry
        await self.audit_service.log(
            action="ORG_CREATED",
            resource_type="Organization",
            resource_id=str(new_org.id),
            organization_id=new_org.id,
            user_id=current_user.id,
            details={"name": new_org.name, "slug": new_org.slug},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return OrganizationResponse.model_validate(new_org)

    async def get_organization_by_id(
        self,
        org_id: uuid.UUID,
        current_user: User,
    ) -> OrganizationResponse:
        # Access Check: Admins and members can only access their own organization
        if current_user.organization_id != org_id:
            raise AuthorizationException("You do not have permission to view this organization.")

        org = await self.repository.get_by_id(org_id)
        if not org:
            raise EntityNotFoundException("Organization", org_id)

        return OrganizationResponse.model_validate(org)

    async def list_organizations(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[OrganizationResponse], int]:
        # Scoped to own org
        if not current_user.organization_id:
            return [], 0
        org = await self.repository.get_by_id(current_user.organization_id)
        if not org:
            return [], 0
        return [OrganizationResponse.model_validate(org)], 1

    async def update_organization(
        self,
        org_id: uuid.UUID,
        org_in: OrganizationUpdate,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> OrganizationResponse:
        if current_user.role.name != RoleType.ADMIN.value or current_user.organization_id != org_id:
            raise AuthorizationException("You are not authorized to update this organization.")

        org = await self.repository.get_by_id(org_id)
        if not org:
            raise EntityNotFoundException("Organization", org_id)

        update_dict = org_in.model_dump(exclude_unset=True)
        updated_org = await self.repository.update(org, update_dict)

        await self.audit_service.log(
            action="ORG_UPDATED",
            resource_type="Organization",
            resource_id=str(updated_org.id),
            organization_id=updated_org.id,
            user_id=current_user.id,
            details=update_dict,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return OrganizationResponse.model_validate(updated_org)

    async def delete_organization(
        self,
        org_id: uuid.UUID,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        if current_user.role.name != RoleType.ADMIN.value or current_user.organization_id != org_id:
            raise AuthorizationException("Only organization administrators can delete the organization.")

        org = await self.repository.get_by_id(org_id)
        if not org:
            raise EntityNotFoundException("Organization", org_id)

        await self.repository.delete(org)

        await self.audit_service.log(
            action="ORG_DELETED",
            resource_type="Organization",
            resource_id=str(org_id),
            organization_id=None,
            user_id=current_user.id,
            details={"deleted_org_name": org.name},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def get_invite_code(self, current_user: User) -> dict:
        role_name = current_user.role.name if hasattr(current_user.role, "name") else str(current_user.role)
        if role_name != RoleType.ADMIN.value or not current_user.organization_id:
            raise AuthorizationException("Only organization administrators can view the invite code.")

        org = await self.repository.get_by_id(current_user.organization_id)
        if not org:
            raise EntityNotFoundException("Organization", current_user.organization_id)

        # Requirement 5: If invite_code is null or empty, auto-generate, persist in DB, and return
        if not org.invite_code or not org.invite_code.strip():
            new_code = generate_organization_invite_code()
            org.invite_code = new_code
            await self.db.flush()
            await self.db.refresh(org)

            await self.audit_service.log(
                action="INVITE_CODE_AUTO_GENERATED",
                resource_type="Organization",
                resource_id=str(org.id),
                organization_id=org.id,
                user_id=current_user.id,
                details={"auto_generated_invite_code": new_code},
            )

        return {"invite_code": org.invite_code, "organization_name": org.name}

    async def regenerate_invite_code(
        self,
        current_user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        role_name = current_user.role.name if hasattr(current_user.role, "name") else str(current_user.role)
        if role_name != RoleType.ADMIN.value or not current_user.organization_id:
            raise AuthorizationException("Only organization administrators can regenerate the invite code.")

        org = await self.repository.get_by_id(current_user.organization_id)
        if not org:
            raise EntityNotFoundException("Organization", current_user.organization_id)

        new_code = generate_organization_invite_code()
        org.invite_code = new_code
        await self.db.flush()
        await self.db.refresh(org)

        await self.audit_service.log(
            action="INVITE_CODE_REGENERATED",
            resource_type="Organization",
            resource_id=str(org.id),
            organization_id=org.id,
            user_id=current_user.id,
            details={"new_invite_code": new_code},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {"invite_code": org.invite_code, "organization_name": org.name}

    async def list_employees(self, current_user: User) -> List[UserResponse]:
        if current_user.role.name != RoleType.ADMIN.value or not current_user.organization_id:
            raise AuthorizationException("Only organization administrators can view employees.")

        stmt = (
            select(User)
            .options(selectinload(User.role))
            .where(User.organization_id == current_user.organization_id)
            .order_by(User.created_at.asc())
        )
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        return [UserResponse.model_validate(u) for u in users]

