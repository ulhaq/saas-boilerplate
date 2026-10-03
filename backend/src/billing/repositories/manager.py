"""Billing extension of the foundation repository manager.

Billing services and routers depend on this subclass instead of the foundation
``RepositoryManager`` so the foundation stays free of billing repositories.
Hook handlers that receive a foundation manager wrap its session via
``BillingRepositoryManager(repos.db)`` to join the same transaction.
"""

from functools import cached_property

from src.billing.repositories.account import BillingAccountRepository
from src.billing.repositories.billing import (
    PlanFeatureRepository,
    PlanPriceRepository,
    PlanRepository,
    PlanSettingRepository,
    PlanUsageRepository,
    SubscriptionRepository,
    WebhookEventRepository,
)
from src.foundation.repositories.repository_manager import RepositoryManager


class BillingRepositoryManager(RepositoryManager):
    @cached_property
    def billing_account(self) -> BillingAccountRepository:
        return BillingAccountRepository(self.db)

    @cached_property
    def plan(self) -> PlanRepository:
        return PlanRepository(self.db)

    @cached_property
    def plan_price(self) -> PlanPriceRepository:
        return PlanPriceRepository(self.db)

    @cached_property
    def plan_feature(self) -> PlanFeatureRepository:
        return PlanFeatureRepository(self.db)

    @cached_property
    def plan_setting(self) -> PlanSettingRepository:
        return PlanSettingRepository(self.db)

    @cached_property
    def plan_usage(self) -> PlanUsageRepository:
        return PlanUsageRepository(self.db)

    @cached_property
    def subscription(self) -> SubscriptionRepository:
        return SubscriptionRepository(self.db)

    @cached_property
    def webhook_event(self) -> WebhookEventRepository:
        return WebhookEventRepository(self.db)
