"""Entitlements from the organization's plan: the features it includes, its
limits (plan settings) and per-period usage counters."""

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.repositories.manager import BillingRepositoryManager


def current_period_start() -> date:
    return datetime.now(tz=UTC).date().replace(day=1)


class PlanEntitlements:
    async def has_feature(
        self,
        db: AsyncSession,
        organization_id: int,
        feature: str,
    ) -> bool:
        repos = BillingRepositoryManager(db)
        return feature in await repos.plan_feature.get_features_for_organization(
            organization_id,
        )

    async def limit(
        self,
        db: AsyncSession,
        organization_id: int,
        metric: str,
    ) -> int | None:
        repos = BillingRepositoryManager(db)
        setting = await repos.plan_setting.get_for_organization(organization_id, metric)
        return setting.value if setting is not None else None

    async def consume(
        self,
        db: AsyncSession,
        organization_id: int,
        metric: str,
    ) -> bool:
        limit = await self.limit(db, organization_id, metric)
        repos = BillingRepositoryManager(db)
        consumed = await repos.plan_usage.consume(
            organization_id,
            metric,
            current_period_start(),
            limit,
        )
        return consumed is not None
