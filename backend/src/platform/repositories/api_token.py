from datetime import UTC, datetime

from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.api_token import ApiToken
from src.platform.repositories.abc import RepositoryABC


class ApiTokenRepository(RepositoryABC[ApiToken]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ApiToken, db)

    async def create(
        self,
        *,
        user_id: int,
        organization_id: int,
        name: str,
        token_hash: str,
        token_prefix: str,
        permissions: list[str],
        expires_at: datetime | None,
    ) -> ApiToken:
        instance = ApiToken(
            user_id=user_id,
            organization_id=organization_id,
            name=name,
            token_hash=token_hash,
            token_prefix=token_prefix,
            permissions=permissions,
            expires_at=expires_at,
        )
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def list_for_user_org(
        self, user_id: int, organization_id: int
    ) -> list[ApiToken]:
        stmt = (
            select(ApiToken)
            .where(
                ApiToken.user_id == user_id,
                ApiToken.organization_id == organization_id,
                ApiToken.revoked_at.is_(None),
            )
            .order_by(
                case(
                    (
                        ApiToken.expires_at.isnot(None)
                        & (ApiToken.expires_at < datetime.now(UTC)),
                        1,
                    ),
                    else_=0,
                ),
                ApiToken.created_at.desc(),
            )
        )
        rs = await self.db.execute(stmt)
        return list(rs.scalars().all())

    async def list_all_for_user(self, user_id: int) -> list[ApiToken]:
        stmt = (
            select(ApiToken)
            .where(ApiToken.user_id == user_id, ApiToken.revoked_at.is_(None))
            .order_by(
                case(
                    (
                        ApiToken.expires_at.isnot(None)
                        & (ApiToken.expires_at < datetime.now(UTC)),
                        1,
                    ),
                    else_=0,
                ),
                ApiToken.created_at.desc(),
            )
        )
        rs = await self.db.execute(stmt)
        return list(rs.scalars().all())

    async def get_by_id(
        self, token_id: int, user_id: int, organization_id: int
    ) -> ApiToken | None:
        stmt = select(ApiToken).where(
            ApiToken.id == token_id,
            ApiToken.user_id == user_id,
            ApiToken.organization_id == organization_id,
            ApiToken.revoked_at.is_(None),
        )
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()

    async def get_by_hash(self, token_hash: str) -> ApiToken | None:
        stmt = select(ApiToken).where(
            ApiToken.token_hash == token_hash,
            ApiToken.revoked_at.is_(None),
        )
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()

    async def revoke(self, token_id: int, user_id: int, organization_id: int) -> bool:
        stmt = (
            update(ApiToken)
            .where(
                ApiToken.id == token_id,
                ApiToken.user_id == user_id,
                ApiToken.organization_id == organization_id,
                ApiToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user_org(self, user_id: int, organization_id: int) -> None:
        stmt = (
            update(ApiToken)
            .where(
                ApiToken.user_id == user_id,
                ApiToken.organization_id == organization_id,
                ApiToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)

    async def touch_last_used(self, token_id: int, organization_id: int) -> None:
        stmt = (
            update(ApiToken)
            .where(ApiToken.id == token_id, ApiToken.organization_id == organization_id)
            .values(last_used_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
