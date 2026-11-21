import uuid
from typing import Callable, List
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    InactiveOrganizationException,
    InactiveUserException,
)
from app.database.session import get_db
from app.models.role import RoleType
from app.models.user import User
from app.security.tokens import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to retrieve and authenticate current user via Bearer token."""
    if not token:
        raise AuthenticationException("Authorization Bearer token is missing")

    payload = decode_access_token(token)
    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationException("Token subject claim is missing")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationException("Malformed subject identifier in token")

    query = (
        select(User)
        .options(selectinload(User.role), selectinload(User.organization))
        .where(User.id == user_uuid)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationException("User referenced by credentials does not exist")

    if not user.is_active:
        raise InactiveUserException("User account has been disabled")

    # If user belongs to an organization, verify org is active
    if user.organization and not user.organization.is_active:
        raise InactiveOrganizationException("Your organization account is inactive")

    return user


def require_roles(allowed_roles: List[RoleType]) -> Callable:
    """Role-Based Access Control dependency factory."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_name = current_user.role.name
        allowed_names = [role.value for role in allowed_roles]

        if user_role_name not in allowed_names:
            raise AuthorizationException(
                f"Role '{user_role_name}' is not permitted to access this resource. Allowed: {allowed_names}"
            )
        return current_user

    return role_checker

