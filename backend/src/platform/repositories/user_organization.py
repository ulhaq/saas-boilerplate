from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.organization import Organization
from src.platform.models.user_organization import UserOrganization
from src.platform.repositories.base import SQLResourceRepository


class UserOrganizationRepository(SQLResourceRepository[UserOrganization]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(UserOrganization, db)

    async def get_by_user_and_organization(
        self, user_id: int, organization_id: int
    ) -> UserOrganization | None:
        stmt = select(UserOrganization).where(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == organization_id,
        )
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()

    async def get_all_for_user(self, user_id: int) -> Sequence[UserOrganization]:
        stmt = (
            select(UserOrganization)
            .join(Organization, Organization.id == UserOrganization.organization_id)
            .where(
                UserOrganization.user_id == user_id,
                Organization.deleted_at.is_(None),
            )
            .order_by(
                UserOrganization.last_active_at.desc().nulls_last(),
                UserOrganization.created_at.asc(),
            )
        )
        rs = await self.db.execute(stmt)
        return rs.scalars().all()

    async def get_active_organization_for_user(
        self, user_id: int
    ) -> UserOrganization | None:
        """
        Return the most-recently-active membership row.

        Falls back to earliest created if none has ever been active.
        Returns None if the user has no organization memberships.
        """
        rows = await self.get_all_for_user(user_id)
        return rows[0] if rows else None

    async def get_all_members_of_organization(
        self, organization_id: int
    ) -> Sequence[UserOrganization]:
        stmt = select(UserOrganization).where(
            UserOrganization.organization_id == organization_id
        )
        rs = await self.db.execute(stmt)
        return rs.scalars().all()

    async def update_last_active(
        self, membership: UserOrganization
    ) -> UserOrganization:
        return await self.update(membership, last_active_at=datetime.now(UTC))
