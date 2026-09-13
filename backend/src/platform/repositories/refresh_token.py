from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.enums import RefreshTokenRevokeReason
from src.platform.models.refresh_token import RefreshToken
from src.platform.models.user import User


class RefreshTokenRepository:
    """One row per session/device, keyed by the refresh JWT's jti.

    Rotation and logout revoke rows in place (tombstones) so a replayed token
    can be classified: a rotated token coming back is a theft signal, a
    logged-out one is a benign retry. Tombstones are removed by the GDPR
    purge once expired.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, user: User, hashed_token: str, expires_at: datetime, jti: str
    ) -> RefreshToken:
        instance = RefreshToken(
            user_id=user.id, token=hashed_token, expires_at=expires_at, jti=jti
        )
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        """Returns the session row (including revoked tombstones) if not expired."""
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.jti == jti)
            .where(RefreshToken.expires_at > datetime.now(UTC))
        )
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def revoke_by_jti(self, jti: str, reason: RefreshTokenRevokeReason) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.jti == jti)
            .values(revoked_at=datetime.now(UTC), revoked_reason=reason)
        )
        await self.db.execute(stmt)

    async def delete_by_user(self, user: User) -> None:
        """Revoke every session for a user (password reset, account removal,
        suspected token theft)."""
        stmt = delete(RefreshToken).where(RefreshToken.user_id == user.id)
        await self.db.execute(stmt)

    async def delete_expired_for_user(self, user: User) -> None:
        stmt = delete(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.expires_at <= datetime.now(UTC),
        )
        await self.db.execute(stmt)
