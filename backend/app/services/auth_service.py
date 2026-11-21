import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationException,
    DuplicateEntityException,
    EntityNotFoundException,
    InactiveOrganizationException,
    InactiveUserException,
    TokenValidationException,
    VaultGuardException,
)
from app.models.organization import Organization, generate_organization_invite_code
from app.models.role import Role, RoleType
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    EmployeeJoinRequest,
    InviteCodeValidateResponse,
    LoginRequest,
    OrgAdminRegisterRequest,
    PersonalRegisterRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.security.password import hash_password, verify_password
from app.security.tokens import (
    create_access_token,
    generate_refresh_token_string,
    hash_token,
)
from app.services.audit_service import AuditService


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.token_repo = TokenRepository(db)
        self.audit_service = AuditService(db)

    async def ensure_roles_exist(self) -> None:
        """Seed standard RBAC roles if they don't already exist."""
        for role_type in RoleType:
            existing = await self.user_repo.get_role_by_type(role_type)
            if not existing:
                role_obj = Role(
                    name=role_type.value,
                    description=f"System role for {role_type.value}",
                )
                self.db.add(role_obj)
        await self.db.flush()

    async def register(
        self,
        register_in: RegisterRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        await self.ensure_roles_exist()

        existing_user = await self.user_repo.get_by_email(register_in.email)
        if existing_user:
            raise DuplicateEntityException("User", "email", register_in.email)

        organization: Optional[Organization] = None
        role_type = RoleType.INDIVIDUAL

        if register_in.organization_name:
            # Org registration flow -> User becomes ADMIN
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", register_in.organization_name.lower()).strip("-")
            existing_org = await self.org_repo.get_by_slug(slug)
            if existing_org:
                slug = f"{slug}-{uuid.uuid4().hex[:6]}"

            invite_code = generate_organization_invite_code()
            organization = Organization(
                name=register_in.organization_name,
                slug=slug,
                contact_email=register_in.email,
                invite_code=invite_code,
                is_active=True,
            )
            self.db.add(organization)
            await self.db.flush()
            await self.db.refresh(organization)
            role_type = RoleType.ADMIN

        role = await self.user_repo.get_role_by_type(role_type)
        if not role:
            raise EntityNotFoundException("Role", role_type.value)

        new_user = User(
            email=register_in.email,
            hashed_password=hash_password(register_in.password),
            full_name=register_in.full_name,
            organization_id=organization.id if organization else None,
            role_id=role.id,
            is_active=True,
            is_verified=True,
            last_login_at=datetime.now(timezone.utc),
        )
        new_user.role = role
        if organization:
            new_user.organization = organization
        self.db.add(new_user)
        await self.db.flush()
        new_user.role = role
        if organization:
            new_user.organization = organization

        # Log audit entry
        await self.audit_service.log(
            action="AUTH_REGISTER_SUCCESS",
            resource_type="User",
            resource_id=str(new_user.id),
            organization_id=new_user.organization_id,
            user_id=new_user.id,
            details={"email": new_user.email, "role": role.name},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return await self._generate_token_response(new_user, ip_address, user_agent)

    async def register_personal(
        self,
        register_in: PersonalRegisterRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        """Personal use registration: Role = INDIVIDUAL, organization_id = None."""
        await self.ensure_roles_exist()

        existing_user = await self.user_repo.get_by_email(register_in.email)
        if existing_user:
            raise DuplicateEntityException("User", "email", register_in.email)

        role = await self.user_repo.get_role_by_type(RoleType.INDIVIDUAL)
        if not role:
            raise EntityNotFoundException("Role", RoleType.INDIVIDUAL.value)

        new_user = User(
            email=register_in.email,
            hashed_password=hash_password(register_in.password),
            full_name=register_in.full_name,
            organization_id=None,
            role_id=role.id,
            is_active=True,
            is_verified=True,
            last_login_at=datetime.now(timezone.utc),
        )
        new_user.role = role
        self.db.add(new_user)
        await self.db.flush()
        new_user.role = role

        await self.audit_service.log(
            action="AUTH_REGISTER_PERSONAL_SUCCESS",
            resource_type="User",
            resource_id=str(new_user.id),
            organization_id=None,
            user_id=new_user.id,
            details={"email": new_user.email, "role": RoleType.INDIVIDUAL.value},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return await self._generate_token_response(new_user, ip_address, user_agent)

    async def register_organization(
        self,
        register_in: OrgAdminRegisterRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        """Organization creation: creates org, creates admin, auto-generates invite code."""
        await self.ensure_roles_exist()

        existing_user = await self.user_repo.get_by_email(register_in.email)
        if existing_user:
            raise DuplicateEntityException("User", "email", register_in.email)

        slug = re.sub(r"[^a-zA-Z0-9]+", "-", register_in.organization_name.lower()).strip("-")
        existing_org = await self.org_repo.get_by_slug(slug)
        if existing_org:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        invite_code = generate_organization_invite_code()
        organization = Organization(
            name=register_in.organization_name,
            slug=slug,
            contact_email=register_in.email,
            invite_code=invite_code,
            max_devices=register_in.max_devices,
            storage_quota_bytes=register_in.storage_quota_bytes,
            is_active=True,
        )
        self.db.add(organization)
        await self.db.flush()
        await self.db.refresh(organization)

        role = await self.user_repo.get_role_by_type(RoleType.ADMIN)
        if not role:
            raise EntityNotFoundException("Role", RoleType.ADMIN.value)

        new_user = User(
            email=register_in.email,
            hashed_password=hash_password(register_in.password),
            full_name=register_in.full_name,
            organization_id=organization.id,
            role_id=role.id,
            is_active=True,
            is_verified=True,
            last_login_at=datetime.now(timezone.utc),
        )
        new_user.role = role
        new_user.organization = organization
        self.db.add(new_user)
        await self.db.flush()
        new_user.role = role
        new_user.organization = organization

        await self.audit_service.log(
            action="AUTH_REGISTER_ORG_ADMIN_SUCCESS",
            resource_type="User",
            resource_id=str(new_user.id),
            organization_id=organization.id,
            user_id=new_user.id,
            details={
                "email": new_user.email,
                "organization_name": organization.name,
                "role": RoleType.ADMIN.value,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return await self._generate_token_response(
            new_user,
            ip_address,
            user_agent,
            invite_code=organization.invite_code,
            organization_name=organization.name,
        )

    async def validate_invite_code(self, invite_code: str) -> InviteCodeValidateResponse:
        """Validate organization invite code and return org details."""
        code = invite_code.strip()
        org = await self.org_repo.get_by_invite_code(code)
        if not org:
            return InviteCodeValidateResponse(
                is_valid=False,
                message="Invitation code is invalid.",
            )
        if not org.is_active:
            return InviteCodeValidateResponse(
                is_valid=False,
                message="Invitation code has expired or organization is suspended.",
            )

        # Check organization capacity against max_devices
        emp_count_stmt = select(func.count(User.id)).where(User.organization_id == org.id)
        emp_count_res = await self.db.execute(emp_count_stmt)
        current_emp_count = emp_count_res.scalar_one_or_none() or 0
        if current_emp_count >= org.max_devices:
            return InviteCodeValidateResponse(
                is_valid=False,
                organization_name=org.name,
                message="Organization has reached the maximum employee limit.",
            )

        return InviteCodeValidateResponse(
            is_valid=True,
            organization_name=org.name,
            organization_slug=org.slug,
            message=f"Valid invitation code for {org.name}.",
        )

    async def register_employee_join(
        self,
        register_in: EmployeeJoinRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        """Join organization via invite code: Role = EMPLOYEE."""
        await self.ensure_roles_exist()

        code = register_in.invite_code.strip()
        org = await self.org_repo.get_by_invite_code(code)
        if not org:
            raise VaultGuardException("Invitation code is invalid.", code="INVALID_INVITE_CODE")
        if not org.is_active:
            raise VaultGuardException("Invitation code has expired or organization is suspended.", code="EXPIRED_INVITE_CODE")

        # Check organization capacity
        emp_count_stmt = select(func.count(User.id)).where(User.organization_id == org.id)
        emp_count_res = await self.db.execute(emp_count_stmt)
        current_emp_count = emp_count_res.scalar_one_or_none() or 0
        if current_emp_count >= org.max_devices:
            raise VaultGuardException("Organization has reached the maximum employee limit.", code="ORGANIZATION_CAPACITY_REACHED")

        existing_user = await self.user_repo.get_by_email(register_in.email)
        if existing_user:
            raise DuplicateEntityException("User", "email", register_in.email)

        role = await self.user_repo.get_role_by_type(RoleType.EMPLOYEE)
        if not role:
            raise EntityNotFoundException("Role", RoleType.EMPLOYEE.value)

        new_user = User(
            email=register_in.email,
            hashed_password=hash_password(register_in.password),
            full_name=register_in.full_name,
            organization_id=org.id,
            role_id=role.id,
            is_active=True,
            is_verified=True,
            last_login_at=datetime.now(timezone.utc),
        )
        new_user.role = role
        new_user.organization = org
        self.db.add(new_user)
        await self.db.flush()
        new_user.role = role
        new_user.organization = org

        await self.audit_service.log(
            action="AUTH_REGISTER_EMPLOYEE_SUCCESS",
            resource_type="User",
            resource_id=str(new_user.id),
            organization_id=org.id,
            user_id=new_user.id,
            details={
                "email": new_user.email,
                "organization_name": org.name,
                "role": RoleType.EMPLOYEE.value,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return await self._generate_token_response(
            new_user,
            ip_address,
            user_agent,
            invite_code=org.invite_code,
            organization_name=org.name,
        )

    async def login(
        self,
        login_in: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        user = await self.user_repo.get_by_email(login_in.email)
        if not user or not verify_password(login_in.password, user.hashed_password):
            # Log failed attempt
            await self.audit_service.log(
                action="AUTH_LOGIN_FAILED",
                resource_type="User",
                details={"attempted_email": login_in.email},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise AuthenticationException("Incorrect email or password.")

        if not user.is_active:
            raise InactiveUserException("Your account has been disabled.")

        if user.organization and not user.organization.is_active:
            raise InactiveOrganizationException("Your organization has been disabled.")

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        self.db.add(user)
        await self.db.flush()

        # Log successful login
        await self.audit_service.log(
            action="AUTH_LOGIN_SUCCESS",
            resource_type="User",
            resource_id=str(user.id),
            organization_id=user.organization_id,
            user_id=user.id,
            details={"email": user.email},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return await self._generate_token_response(user, ip_address, user_agent)

    async def refresh_tokens(
        self,
        raw_refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        token_hash_val = hash_token(raw_refresh_token)
        stored_token = await self.token_repo.get_active_token(token_hash_val)

        if not stored_token:
            raise TokenValidationException("Refresh token is invalid, expired, or revoked.")

        # Rotate: revoke current token
        await self.token_repo.revoke_token(token_hash_val)

        user = await self.user_repo.get_by_id(stored_token.user_id)
        if not user or not user.is_active:
            raise AuthenticationException("User is no longer active.")

        # Issue new token pair
        return await self._generate_token_response(user, ip_address, user_agent)

    async def logout(
        self,
        raw_refresh_token: str,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        token_hash_val = hash_token(raw_refresh_token)
        await self.token_repo.revoke_token(token_hash_val)

        await self.audit_service.log(
            action="AUTH_LOGOUT",
            resource_type="User",
            resource_id=str(user.id),
            organization_id=user.organization_id,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def _generate_token_response(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        invite_code: Optional[str] = None,
        organization_name: Optional[str] = None,
    ) -> TokenResponse:
        role_name = user.role.name if user.role else RoleType.INDIVIDUAL.value
        access_token = create_access_token(
            subject=str(user.id),
            role=role_name,
            organization_id=str(user.organization_id) if user.organization_id else None,
        )
        refresh_raw = generate_refresh_token_string()
        refresh_hash = hash_token(refresh_raw)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self.token_repo.create_refresh_token(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        user_response = UserResponse.model_validate(user)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_raw,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response,
            invite_code=invite_code,
            organization_name=organization_name,
        )

