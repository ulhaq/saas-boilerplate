"""Tests for billing repositories, the provider factory, plan entitlements and
the platform's require_limit over them."""

import asyncio
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import override
from unittest.mock import MagicMock

import pytest

from src.billing.models.billing import (
    Plan,
    PlanPrice,
    PlanSetting,
    WebhookEvent,
)
from src.billing.models.billing import PlanFeature as PlanFeatureModel
from src.billing.provider.dependencies import get_billing_provider
from src.billing.provider.stripe_provider import StripeProvider
from src.billing.repositories.manager import BillingRepositoryManager
from src.billing.services.entitlements import PlanEntitlements, current_period_start
from src.platform.core.entitlements import Entitlements
from src.platform.core.exceptions import LimitExceededException
from src.platform.core.security import Auth
from src.platform.enums import Permission as PermEnum
from src.platform.enums import PlanFeature
from src.platform.models.organization import Organization
from tests.conftest import TestSessionLocal


class _Metric(StrEnum):
    API_CALLS = "api_calls"


def _admin_auth(org_id: int = 1) -> Auth:
    return Auth(
        id=1,
        name="Alice",
        email="admin@example.org",
        organization_id=org_id,
        roles=["Owner"],
        permissions=[p.value for p in PermEnum],
    )


# ---------------------------------------------------------------------------
# billing/dependencies.py
# ---------------------------------------------------------------------------


def test_get_billing_provider_returns_stripe_provider():
    provider = get_billing_provider()
    assert isinstance(provider, StripeProvider)


def test_current_period_start_is_first_of_month():
    d = current_period_start()
    assert d.day == 1
    assert isinstance(d, date)


# ---------------------------------------------------------------------------
# require_limit (platform) over the installed Entitlements
# ---------------------------------------------------------------------------


class _FakeEntitlements(Entitlements):
    def __init__(self, *, allows: bool) -> None:
        self._allows = allows
        self.consumed: list[tuple[int, str]] = []

    @override
    async def has_feature(self, db, organization_id, feature) -> bool:
        return True

    @override
    async def limit(self, db, organization_id, metric) -> int | None:
        return None

    @override
    async def consume(self, db, organization_id, metric) -> bool:
        self.consumed.append((organization_id, metric))
        return self._allows


def _install(mocker, entitlements: _FakeEntitlements) -> None:
    mocker.patch(
        "src.platform.services.access.composition.current",
        return_value=MagicMock(entitlements=entitlements),
    )


async def test_require_limit_consumes_one_use(mocker):
    from src.platform.services.access import require_limit

    entitlements = _FakeEntitlements(allows=True)
    _install(mocker, entitlements)
    await require_limit(_Metric.API_CALLS)(db=MagicMock(), current_user=_admin_auth())
    assert entitlements.consumed == [(1, _Metric.API_CALLS)]


async def test_require_limit_exceeded_raises(mocker):
    from src.platform.services.access import require_limit

    _install(mocker, _FakeEntitlements(allows=False))
    check = require_limit(_Metric.API_CALLS)
    with pytest.raises(LimitExceededException):
        await check(db=MagicMock(), current_user=_admin_auth())


# ---------------------------------------------------------------------------
# PlanEntitlements (billing): plan features, plan settings, usage counters
# ---------------------------------------------------------------------------


async def _usage(organization_id: int, metric: str) -> int:
    async with TestSessionLocal() as session:
        return await BillingRepositoryManager(session).plan_usage.get_count(
            organization_id,
            metric,
            current_period_start(),
        )


async def test_plan_entitlements_read_the_organizations_plan():
    entitlements = PlanEntitlements()
    async with TestSessionLocal() as session, session.begin():
        free_price = await BillingRepositoryManager(session).plan_price.get_free_price()
        assert free_price
        session.add(PlanSetting(plan_id=free_price.plan_id, key="api_calls", value=2))
        await session.flush()

        # Seeded: the free plan includes api_token and has no seat limit.
        assert await entitlements.has_feature(session, 1, PlanFeature.API_TOKEN)
        assert not await entitlements.has_feature(session, 1, "sso")
        assert await entitlements.limit(session, 1, "api_calls") == 2
        assert await entitlements.limit(session, 1, "seats") is None

        # Two uses fit the limit of 2; the third doesn't, and isn't counted.
        assert await entitlements.consume(session, 1, "api_calls")
        assert await entitlements.consume(session, 1, "api_calls")
        assert not await entitlements.consume(session, 1, "api_calls")
        # Unlimited metrics are counted too.
        assert await entitlements.consume(session, 1, "exports")

    assert await _usage(1, "api_calls") == 2
    assert await _usage(1, "exports") == 1
    assert await _usage(2, "api_calls") == 0


async def test_a_zero_limit_allows_nothing():
    async with TestSessionLocal() as session, session.begin():
        free_price = await BillingRepositoryManager(session).plan_price.get_free_price()
        assert free_price
        session.add(PlanSetting(plan_id=free_price.plan_id, key="api_calls", value=0))
        await session.flush()
        assert not await PlanEntitlements().consume(session, 1, "api_calls")
    assert await _usage(1, "api_calls") == 0


async def test_concurrent_uses_never_overshoot_the_limit():
    """Many requests at once, 3 units left: exactly 3 succeed."""
    async with TestSessionLocal() as session, session.begin():
        free_price = await BillingRepositoryManager(session).plan_price.get_free_price()
        assert free_price
        session.add(PlanSetting(plan_id=free_price.plan_id, key="api_calls", value=3))

    async def use() -> bool:
        async with TestSessionLocal() as session, session.begin():
            return await PlanEntitlements().consume(session, 1, "api_calls")

    results = await asyncio.gather(*(use() for _ in range(10)))

    assert results.count(True) == 3
    assert await _usage(1, "api_calls") == 3


# ---------------------------------------------------------------------------
# PlanRepository
# ---------------------------------------------------------------------------


async def test_plan_get_by_external_product_id_found():
    async with TestSessionLocal() as session, session.begin():
        plan = Plan(name="Test Plan", is_active=True, external_product_id="prod_abc")
        session.add(plan)
        await session.flush()
        repos = BillingRepositoryManager(session)
        result = await repos.plan.get_by_external_product_id("prod_abc")
        assert result is not None
        assert result.external_product_id == "prod_abc"


async def test_plan_get_by_external_product_id_not_found():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        result = await repos.plan.get_by_external_product_id("prod_nonexistent")
        assert result is None


async def test_plan_get_active_plans():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        plans = await repos.plan.get_active_plans()
        assert len(plans) >= 1
        assert all(p.is_active for p in plans)


# ---------------------------------------------------------------------------
# PlanPriceRepository
# ---------------------------------------------------------------------------


async def test_plan_price_get_by_plan():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        # Get the seeded free plan (id=1)
        plans = await repos.plan.get_active_plans()
        free_plan = plans[0]
        prices = await repos.plan_price.get_by_plan(free_plan.id)
        assert len(prices) >= 1


async def test_plan_price_get_by_external_price_id_found():
    async with TestSessionLocal() as session, session.begin():
        plan = Plan(name="Ext Plan", is_active=True, external_product_id="prod_ext")
        session.add(plan)
        await session.flush()
        price = PlanPrice(
            plan_id=plan.id,
            amount=500,
            currency="usd",
            interval="month",
            interval_count=1,
            external_price_id="price_ext_abc",
            is_active=True,
        )
        session.add(price)
        await session.flush()
        repos = BillingRepositoryManager(session)
        result = await repos.plan_price.get_by_external_price_id("price_ext_abc")
        assert result is not None
        assert result.external_price_id == "price_ext_abc"


async def test_plan_price_get_by_external_price_id_not_found():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        result = await repos.plan_price.get_by_external_price_id("price_nonexistent")
        assert result is None


async def test_plan_price_get_free_price():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        result = await repos.plan_price.get_free_price()
        assert result is not None
        assert result.amount == 0


async def test_plan_price_get_highest_price():
    async with TestSessionLocal() as session, session.begin():
        plan = Plan(name="Paid Plan", is_active=True, external_product_id="prod_paid")
        session.add(plan)
        await session.flush()
        price = PlanPrice(
            plan_id=plan.id,
            amount=999,
            currency="usd",
            interval="month",
            interval_count=1,
            external_price_id="price_highest",
            is_active=True,
        )
        session.add(price)
        await session.flush()
        repos = BillingRepositoryManager(session)
        result = await repos.plan_price.get_highest_price()
        assert result is not None
        assert result.amount == 999


async def test_plan_price_get_active_by_plan():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        plans = await repos.plan.get_active_plans()
        free_plan = plans[0]
        prices = await repos.plan_price.get_active_by_plan(free_plan.id)
        assert len(prices) >= 1
        assert all(p.is_active for p in prices)


async def test_plan_price_has_active_subscriptions_true():
    """The seeded free price has an active subscription for org 1."""
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        free_price = await repos.plan_price.get_free_price()
        assert free_price is not None
        result = await repos.plan_price.has_active_subscriptions(free_price.id)
        assert result is True


async def test_plan_price_has_active_subscriptions_false():
    async with TestSessionLocal() as session, session.begin():
        plan = Plan(name="No Sub Plan", is_active=True)
        session.add(plan)
        await session.flush()
        price = PlanPrice(
            plan_id=plan.id,
            amount=100,
            currency="usd",
            interval="month",
            interval_count=1,
            is_active=True,
        )
        session.add(price)
        await session.flush()
        repos = BillingRepositoryManager(session)
        result = await repos.plan_price.has_active_subscriptions(price.id)
        assert result is False


# ---------------------------------------------------------------------------
# PlanFeatureRepository
# ---------------------------------------------------------------------------


async def test_plan_feature_get_features_for_organization():
    """Org 1 has an active free subscription; free plan has API_TOKEN feature."""
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        features = await repos.plan_feature.get_features_for_organization(1)
        assert PlanFeature.API_TOKEN in features


# ---------------------------------------------------------------------------
# SubscriptionRepository
# ---------------------------------------------------------------------------


async def test_subscription_get_active_for_organization_found():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        repos.subscription.set_organization_scope(1)
        result = await repos.subscription.get_active_for_organization(1)
        assert result is not None
        assert result.status == "active"


async def test_subscription_get_active_for_organization_not_found():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        result = await repos.subscription.get_active_for_organization(9999)
        assert result is None


async def test_subscription_get_active_for_organization_locked():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        repos.subscription.set_organization_scope(1)
        result = await repos.subscription.get_active_for_organization_locked(1)
        assert result is not None


async def _fresh_org(session) -> int:
    """Create and flush a new organization, returning its id."""
    org = Organization(name="Temp Org")
    session.add(org)
    await session.flush()
    return org.id


async def test_subscription_get_by_external_subscription_id_found():
    async with TestSessionLocal() as session, session.begin():
        org_id = await _fresh_org(session)
        repos = BillingRepositoryManager(session)
        free_price = await repos.plan_price.get_free_price()
        assert free_price is not None
        sub = await repos.subscription.create(
            organization_id=org_id,
            plan_price_id=free_price.id,
            status="active",
            external_subscription_id="sub_ext_find_me",
        )
        result = await repos.subscription.get_by_external_subscription_id(
            "sub_ext_find_me",
        )
        assert result is not None
        assert result.id == sub.id


async def test_subscription_get_by_external_subscription_id_not_found():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        result = await repos.subscription.get_by_external_subscription_id("sub_nope")
        assert result is None


async def test_subscription_get_by_external_subscription_id_locked():
    async with TestSessionLocal() as session, session.begin():
        org_id = await _fresh_org(session)
        repos = BillingRepositoryManager(session)
        free_price = await repos.plan_price.get_free_price()
        assert free_price is not None
        await repos.subscription.create(
            organization_id=org_id,
            plan_price_id=free_price.id,
            status="active",
            external_subscription_id="sub_ext_locked",
        )
        result = await repos.subscription.get_by_external_subscription_id_locked(
            "sub_ext_locked",
        )
        assert result is not None


async def test_subscription_get_stale_incomplete():
    async with TestSessionLocal() as session, session.begin():
        org_id = await _fresh_org(session)
        repos = BillingRepositoryManager(session)
        free_price = await repos.plan_price.get_free_price()
        assert free_price is not None
        stale_sub = await repos.subscription.create(
            organization_id=org_id,
            plan_price_id=free_price.id,
            status="incomplete",
        )
        stale_sub.created_at = datetime.now(UTC) - timedelta(days=2)
        session.add(stale_sub)
        await session.flush()

        threshold = datetime.now(UTC) - timedelta(days=1)
        results = await repos.subscription.get_stale_incomplete_subscriptions(threshold)
        assert any(s.id == stale_sub.id for s in results)


async def test_subscription_bulk_cancel_stale_incomplete():
    async with TestSessionLocal() as session, session.begin():
        org_id = await _fresh_org(session)
        repos = BillingRepositoryManager(session)
        free_price = await repos.plan_price.get_free_price()
        assert free_price is not None
        stale_sub = await repos.subscription.create(
            organization_id=org_id,
            plan_price_id=free_price.id,
            status="incomplete",
        )
        stale_sub.created_at = datetime.now(UTC) - timedelta(days=2)
        session.add(stale_sub)
        await session.flush()

        threshold = datetime.now(UTC) - timedelta(days=1)
        count = await repos.subscription.bulk_cancel_stale_incomplete(threshold)
        assert count >= 1


async def test_subscription_create_or_get_active():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        free_price = await repos.plan_price.get_free_price()
        assert free_price is not None
        sub = await repos.subscription.create_or_get_active(
            organization_id=1,
            plan_price_id=free_price.id,
            status="incomplete",
        )
        assert sub is not None


# ---------------------------------------------------------------------------
# PlanSettingRepository
# ---------------------------------------------------------------------------


async def test_plan_setting_get_for_organization():
    """Create a limit for the free plan, verify it's returned for org 1's active sub."""
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        free_price = await repos.plan_price.get_free_price()
        assert free_price is not None
        plan_id = free_price.plan_id
        limit = PlanSetting(plan_id=plan_id, key=_Metric.API_CALLS, value=100)
        session.add(limit)
        await session.flush()

        result = await repos.plan_setting.get_for_organization(1, _Metric.API_CALLS)
        assert result is not None
        assert result.value == 100


async def test_plan_setting_get_settings_for_organization():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        free_price = await repos.plan_price.get_free_price()
        assert free_price is not None
        plan_id = free_price.plan_id
        limit = PlanSetting(plan_id=plan_id, key=_Metric.API_CALLS, value=50)
        session.add(limit)
        await session.flush()

        results = await repos.plan_setting.get_settings_for_organization(1)
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# PlanUsageRepository
# ---------------------------------------------------------------------------


async def test_plan_usage_get_count_zero():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        count = await repos.plan_usage.get_count(
            organization_id=1,
            metric=_Metric.API_CALLS,
            period_start=datetime.now(tz=UTC).date(),
        )
        assert count == 0


async def test_plan_usage_get_for_organization_empty():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        records = await repos.plan_usage.get_for_organization(
            organization_id=1,
            period_start=datetime.now(tz=UTC).date(),
        )
        assert records == [] or len(records) == 0


# ---------------------------------------------------------------------------
# WebhookEventRepository
# ---------------------------------------------------------------------------


async def _create_webhook_event(
    session,
    external_event_id: str = "evt_test",
) -> WebhookEvent:
    repos = BillingRepositoryManager(session)
    return await repos.webhook_event.create(
        external_event_id=external_event_id,
        event_type="customer.subscription.updated",
        status="received",
    )


async def test_webhook_event_get_by_external_event_id_found():
    async with TestSessionLocal() as session, session.begin():
        event = await _create_webhook_event(session, "evt_find_me")
        repos = BillingRepositoryManager(session)
        result = await repos.webhook_event.get_by_external_event_id("evt_find_me")
        assert result is not None
        assert result.id == event.id


async def test_webhook_event_get_by_external_event_id_not_found():
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        result = await repos.webhook_event.get_by_external_event_id("evt_nope")
        assert result is None


async def test_webhook_event_mark_processed():
    async with TestSessionLocal() as session, session.begin():
        event = await _create_webhook_event(session, "evt_process_me")
        repos = BillingRepositoryManager(session)
        updated = await repos.webhook_event.mark_processed(event)
        assert updated.status == "processed"
        assert updated.processed_at is not None


async def test_webhook_event_mark_failed():
    async with TestSessionLocal() as session, session.begin():
        event = await _create_webhook_event(session, "evt_fail_me")
        repos = BillingRepositoryManager(session)
        updated = await repos.webhook_event.mark_failed(event, "something went wrong")
        assert updated.status == "failed"
        assert updated.error == "something went wrong"


# ---------------------------------------------------------------------------
# Access policy: whose plan applies (ENTITLED_STATUSES, else the free plan)
# ---------------------------------------------------------------------------


async def _paid_plan(session) -> tuple[int, int]:
    """A paid plan with the `sso` feature and 50 seats; returns (plan, price)."""
    plan = Plan(name="Paid", is_active=True)
    session.add(plan)
    await session.flush()
    price = PlanPrice(
        plan_id=plan.id,
        amount=999,
        currency="dkk",
        interval="month",
        is_active=True,
    )
    session.add(price)
    session.add(PlanSetting(plan_id=plan.id, key="seats", value=50))
    session.add(PlanFeatureModel(plan_id=plan.id, feature="sso"))
    await session.flush()
    return plan.id, price.id


@pytest.mark.parametrize(
    ("status", "paid_plan_applies"),
    [
        ("active", True),
        ("trialing", True),
        ("past_due", True),
        # A trial that ended without a card: still live, but on the free plan.
        ("paused", False),
        ("incomplete", False),
        ("canceled", False),
    ],
)
async def test_the_paid_plan_applies_only_while_entitled(status, paid_plan_applies):
    entitlements = PlanEntitlements()
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        _, price_id = await _paid_plan(session)
        free_price = await repos.plan_price.get_free_price()
        assert free_price
        session.add(PlanSetting(plan_id=free_price.plan_id, key="seats", value=1))
        sub = await repos.subscription.get_active_for_organization(1)
        assert sub
        await repos.subscription.update(sub, plan_price_id=price_id, status=status)

        assert await entitlements.has_feature(session, 1, "sso") is paid_plan_applies
        assert await entitlements.limit(session, 1, "seats") == (
            50 if paid_plan_applies else 1
        )
        # The free plan's own feature applies whenever the paid plan doesn't.
        assert (
            await entitlements.has_feature(session, 1, PlanFeature.API_TOKEN)
            is not paid_plan_applies
        )


async def test_an_organization_without_a_subscription_is_on_the_free_plan():
    entitlements = PlanEntitlements()
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        free_price = await repos.plan_price.get_free_price()
        assert free_price
        session.add(PlanSetting(plan_id=free_price.plan_id, key="seats", value=1))
        sub = await repos.subscription.get_active_for_organization(1)
        assert sub
        await session.delete(sub)
        await session.flush()

        assert await entitlements.limit(session, 1, "seats") == 1
        assert await entitlements.has_feature(session, 1, PlanFeature.API_TOKEN)
