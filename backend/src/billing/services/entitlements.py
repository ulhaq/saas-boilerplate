"""Entitlements from the organization's plan: the features it includes, its
limits (plan settings) and per-period usage counters."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.repositories.manager import BillingRepositoryManager


def current_period_start() -> date:
    return date.today().replace(day=1)


class PlanEntitlements:
    async def has_feature(
        self, db: AsyncSession, organization_id: int, feature: str
    ) -> bool:
        repos = BillingRepositoryManager(db)
        return feature in await repos.plan_feature.get_features_for_organization(
            organization_id
        )

    async def limit(
        self, db: AsyncSession, organization_id: int, metric: str
    ) -> int | None:
        repos = BillingRepositoryManager(db)
        setting = await repos.plan_setting.get_for_organization(organization_id, metric)
        return setting.value if setting is not None else None

    async def usage(self, db: AsyncSession, organization_id: int, metric: str) -> int:
        repos = BillingRepositoryManager(db)
        return await repos.plan_usage.get_count(
            organization_id, metric, current_period_start()
        )

    async def record_usage(
        self, db: AsyncSession, organization_id: int, metric: str
    ) -> int:
        repos = BillingRepositoryManager(db)
        return await repos.plan_usage.increment(
            organization_id, metric, current_period_start()
        )
