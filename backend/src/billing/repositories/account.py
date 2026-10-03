from datetime import datetime

from sqlalchemy import Select, and_, exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models.account import BillingAccount
from src.billing.models.billing import PlanPrice, Subscription
from src.platform.models.organization import Organization
from src.platform.repositories.base import SQLResourceRepository


class BillingAccountRepository(SQLResourceRepository[BillingAccount]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(BillingAccount, db)

    async def get_for_organization(self, organization_id: int) -> BillingAccount | None:
        """The account of a live (not deleted) organization."""
        stmt = self._live().filter(self.model.organization_id == organization_id)
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def get_by_external_customer_id(
        self, external_customer_id: str
    ) -> BillingAccount | None:
        rs = await self.db.execute(self._by_customer(external_customer_id))
        return rs.unique().scalar_one_or_none()

    async def get_by_external_customer_id_locked(
        self, external_customer_id: str
    ) -> BillingAccount | None:
        """
        Like get_by_external_customer_id but acquires a row lock (SELECT FOR UPDATE).
        Use in webhook handlers to prevent concurrent
        processing on the same organization.
        """
        stmt = self._by_customer(external_customer_id).with_for_update(of=self.model)
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    def _by_customer(self, external_customer_id: str) -> Select:
        return self._live().filter(
            self.model.external_customer_id == external_customer_id
        )

    def _live(self) -> Select:
        """Accounts of organizations that are not deleted."""
        return (
            select(self.model)
            .join(Organization, Organization.id == self.model.organization_id)
            .filter(Organization.deleted_at.is_(None))
        )

    async def get_pending_customer_syncs(
        self, limit: int = 100
    ) -> list[BillingAccount]:
        """Accounts whose provider customer is waiting for an email update."""
        stmt = (
            self._live()
            .filter(
                self.model.pending_customer_email.is_not(None),
                self.model.external_customer_id.is_not(None),
            )
            .order_by(self.model.updated_at)
            .limit(limit)
        )
        rs = await self.db.execute(stmt)
        return list(rs.unique().scalars().all())

    async def clear_pending_customer_email(self, account_id: int, email: str) -> bool:
        """Mark ``email`` as synced - unless a newer change replaced it meanwhile,
        which then stays pending for the next sync."""
        rs = await self.db.execute(
            update(self.model)
            .where(
                self.model.id == account_id,
                self.model.pending_customer_email == email,
            )
            .values(pending_customer_email=None)
        )
        return bool(rs.rowcount)

    async def get_trial_reminder_candidates(
        self, created_before: datetime, limit: int = 500
    ) -> list[BillingAccount]:
        """Accounts eligible for the "trial still available" reminder.

        An account qualifies when its organization was created before
        ``created_before``, has never used its trial, has not been reminded yet,
        and has no subscription that would make ``start_trial`` fail - i.e. no
        trialing, past_due or paused subscription and no active paid one.
        Mirrors the guards in ``SubscriptionService.start_trial`` so the email
        is only sent to organizations that can actually act on it.
        """
        blocking_subscription = exists().where(
            and_(
                Subscription.organization_id == self.model.organization_id,
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
            .join(Organization, Organization.id == self.model.organization_id)
            .filter(
                Organization.deleted_at.is_(None),
                Organization.created_at <= created_before,
                self.model.trial_used.is_(False),
                self.model.trial_reminder_sent_at.is_(None),
                ~blocking_subscription,
            )
            .order_by(Organization.created_at)
            .limit(limit)
        )
        rs = await self.db.execute(stmt)
        return list(rs.unique().scalars().all())
