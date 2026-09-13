from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.billing import PlanPrice, Subscription
from src.platform.models.organization import Organization
from src.platform.repositories.abc import SoftDeleteRepositoryABC
from src.platform.repositories.base import SoftDeleteRepository


class OrganizationRepositoryABC(SoftDeleteRepositoryABC[Organization], ABC):
    @abstractmethod
    async def get_trial_reminder_candidates(
        self, created_before: datetime, limit: int = 500
    ) -> list[Organization]: ...


class OrganizationRepository(
    SoftDeleteRepository[Organization], OrganizationRepositoryABC
):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Organization, db)

    async def get_by_name(
        self, name: str, include_deleted: bool = False
    ) -> Organization | None:
        return await self._get_by_field("name", name, include_deleted)

    async def get_by_external_customer_id(
        self, external_customer_id: str
    ) -> Organization | None:
        stmt = select(self.model).filter(
            self.model.external_customer_id == external_customer_id,
            self.model.deleted_at.is_(None),
        )
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def get_by_external_customer_id_locked(
        self, external_customer_id: str
    ) -> Organization | None:
        """
        Like get_by_external_customer_id but acquires a row lock (SELECT FOR UPDATE).
        Use in webhook handlers to prevent concurrent
        processing on the same organization.
        """
        stmt = (
            select(self.model)
            .filter(
                self.model.external_customer_id == external_customer_id,
                self.model.deleted_at.is_(None),
            )
            .with_for_update()
        )
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def get_trial_reminder_candidates(
        self, created_before: datetime, limit: int = 500
    ) -> list[Organization]:
        """Organizations eligible for the "trial still available" reminder.

        An organization qualifies when it was created before ``created_before``,
        has never used its trial, has not been reminded yet, and has no
        subscription that would make ``start_trial`` fail - i.e. no trialing,
        past_due or paused subscription and no active paid one. Mirrors the
        guards in ``BillingService.start_trial`` so the email is only sent to
        organizations that can actually act on it.
        """
        blocking_subscription = exists().where(
            and_(
                Subscription.organization_id == Organization.id,
                Subscription.deleted_at.is_(None),
                or_(
                    Subscription.status.in_(("trialing", "past_due", "paused")),
                    and_(
                        Subscription.status == "active",
                        Subscription.plan_price_id == PlanPrice.id,
                        PlanPrice.amount > 0,
                    ),
                ),
            )
        )
        stmt = (
            select(self.model)
            .filter(
                self.model.deleted_at.is_(None),
                self.model.trial_used.is_(False),
                self.model.trial_reminder_sent_at.is_(None),
                self.model.created_at <= created_before,
                ~blocking_subscription,
            )
            .order_by(self.model.created_at)
            .limit(limit)
        )
        rs = await self.db.execute(stmt)
        return list(rs.unique().scalars().all())
