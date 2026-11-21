import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.refresh_token import RefreshToken


class TokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> RefreshToken:
        db_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(db_token)
        await self.db.flush()
        await self.db.refresh(db_token)
        return db_token

    async def get_active_token(self, token_hash: str) -> Optional[RefreshToken]:
        now = datetime.now(timezone.utc)
        query = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > now,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def revoke_token(self, token_hash: str) -> bool:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(is_revoked=True)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> int:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
            .values(is_revoked=True)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

