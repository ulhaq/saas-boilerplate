"""Tests for billing repositories and billing/dependencies.py."""

from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.platform.billing.dependencies import (
    _current_period_start,
    get_billing_provider,
    track_usage,
)
from src.platform.billing.stripe_provider import StripeProvider
from src.platform.core.exceptions import LimitExceededException
from src.platform.core.security import Auth
from src.platform.enums import Permission as PermEnum
from src.platform.enums import PlanFeature
from src.platform.models.billing import (
    Plan,
    PlanPrice,
    PlanSetting,
    WebhookEvent,
)
from src.platform.models.organization import Organization
from src.platform.repositories.repository_manager import RepositoryManager
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
    d = _current_period_start()
    assert d.day == 1
    assert isinstance(d, date)


async def test_require_limit_no_limit_defined_passes():
    """When no limit is configured, the check passes without raising."""
    from src.platform.billing.dependencies import require_limit

    repos = MagicMock()
    repos.plan_setting.get_for_organization = AsyncMock(return_value=None)
    auth = _admin_auth()

    check = require_limit(_Metric.API_CALLS)
    # Directly call the inner _check function
    _ = check.__wrapped__ if hasattr(check, "__wrapped__") else None
    # require_limit returns the inner _check coroutine function directly
    await check(repos=repos, current_user=auth)


async def test_require_limit_within_limit_passes():
    from src.platform.billing.dependencies import require_limit

    limit = MagicMock()
    limit.value = 100
    repos = MagicMock()
    repos.plan_setting.get_for_organization = AsyncMock(return_value=limit)
    repos.plan_usage.get_count = AsyncMock(return_value=50)
    auth = _admin_auth()

    check = require_limit(_Metric.API_CALLS)
    await check(repos=repos, current_user=auth)  # should not raise


async def test_require_limit_unlimited_passes():
    """limit.value = None means unlimited."""
    from src.platform.billing.dependencies import require_limit

    limit = MagicMock()
    limit.value = None
    repos = MagicMock()
    repos.plan_setting.get_for_organization = AsyncMock(return_value=limit)
    auth = _admin_auth()

    check = require_limit(_Metric.API_CALLS)
    await check(repos=repos, current_user=auth)


async def test_require_limit_exceeded_raises():
    from src.platform.billing.dependencies import require_limit

    limit = MagicMock()
    limit.value = 10
    repos = MagicMock()
    repos.plan_setting.get_for_organization = AsyncMock(return_value=limit)
    repos.plan_usage.get_count = AsyncMock(return_value=10)
    auth = _admin_auth()

    check = require_limit(_Metric.API_CALLS)
    with pytest.raises(LimitExceededException):
        await check(repos=repos, current_user=auth)


async def test_track_usage_calls_increment():
    repos = MagicMock()
    repos.plan_usage.increment = AsyncMock(return_value=5)

    result = await track_usage(repos, organization_id=1, metric=_Metric.API_CALLS)
    assert result == 5
    repos.plan_usage.increment.assert_awaited_once()


# ---------------------------------------------------------------------------
# PlanRepository
# ---------------------------------------------------------------------------


async def test_plan_get_by_external_product_id_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            plan = Plan(
                name="Test Plan", is_active=True, external_product_id="prod_abc"
            )
            session.add(plan)
            await session.flush()
            repos = RepositoryManager(session)
            result = await repos.plan.get_by_external_product_id("prod_abc")
            assert result is not None
            assert result.external_product_id == "prod_abc"


async def test_plan_get_by_external_product_id_not_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            result = await repos.plan.get_by_external_product_id("prod_nonexistent")
            assert result is None


async def test_plan_get_active_plans():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            plans = await repos.plan.get_active_plans()
            assert len(plans) >= 1
            assert all(p.is_active for p in plans)


# ---------------------------------------------------------------------------
# PlanPriceRepository
# ---------------------------------------------------------------------------


async def test_plan_price_get_by_plan():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            # Get the seeded free plan (id=1)
            plans = await repos.plan.get_active_plans()
            free_plan = plans[0]
            prices = await repos.plan_price.get_by_plan(free_plan.id)
            assert len(prices) >= 1


async def test_plan_price_get_by_external_price_id_found():
    async with TestSessionLocal() as session:
        async with session.begin():
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
            repos = RepositoryManager(session)
            result = await repos.plan_price.get_by_external_price_id("price_ext_abc")
            assert result is not None
            assert result.external_price_id == "price_ext_abc"


async def test_plan_price_get_by_external_price_id_not_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            result = await repos.plan_price.get_by_external_price_id(
                "price_nonexistent"
            )
            assert result is None


async def test_plan_price_get_free_price():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            result = await repos.plan_price.get_free_price()
            assert result is not None
            assert result.amount == 0


async def test_plan_price_get_highest_price():
    async with TestSessionLocal() as session:
        async with session.begin():
            plan = Plan(
                name="Paid Plan", is_active=True, external_product_id="prod_paid"
            )
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
            repos = RepositoryManager(session)
            result = await repos.plan_price.get_highest_price()
            assert result is not None
            assert result.amount == 999


async def test_plan_price_get_active_by_plan():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            plans = await repos.plan.get_active_plans()
            free_plan = plans[0]
            prices = await repos.plan_price.get_active_by_plan(free_plan.id)
            assert len(prices) >= 1
            assert all(p.is_active for p in prices)


async def test_plan_price_has_active_subscriptions_true():
    """The seeded free price has an active subscription for org 1."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            free_price = await repos.plan_price.get_free_price()
            assert free_price is not None
            result = await repos.plan_price.has_active_subscriptions(free_price.id)
            assert result is True


async def test_plan_price_has_active_subscriptions_false():
    async with TestSessionLocal() as session:
        async with session.begin():
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
            repos = RepositoryManager(session)
            result = await repos.plan_price.has_active_subscriptions(price.id)
            assert result is False


# ---------------------------------------------------------------------------
# PlanFeatureRepository
# ---------------------------------------------------------------------------


async def test_plan_feature_get_features_for_organization():
    """Org 1 has an active free subscription; free plan has API_TOKEN feature."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            features = await repos.plan_feature.get_features_for_organization(1)
            assert PlanFeature.API_TOKEN in features


# ---------------------------------------------------------------------------
# SubscriptionRepository
# ---------------------------------------------------------------------------


async def test_subscription_get_active_for_organization_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            result = await repos.subscription.get_active_for_organization(1)
            assert result is not None
            assert result.status == "active"


async def test_subscription_get_active_for_organization_not_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            result = await repos.subscription.get_active_for_organization(9999)
            assert result is None


async def test_subscription_get_active_for_organization_locked():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            result = await repos.subscription.get_active_for_organization_locked(1)
            assert result is not None


async def _fresh_org(session) -> int:
    """Create and flush a new organization, returning its id."""
    org = Organization(name="Temp Org", billing_email="billing@example.org")
    session.add(org)
    await session.flush()
    return org.id


async def test_subscription_get_by_external_subscription_id_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            org_id = await _fresh_org(session)
            repos = RepositoryManager(session)
            free_price = await repos.plan_price.get_free_price()
            assert free_price is not None
            sub = await repos.subscription.create(
                organization_id=org_id,
                plan_price_id=free_price.id,
                status="active",
                external_subscription_id="sub_ext_find_me",
            )
            result = await repos.subscription.get_by_external_subscription_id(
                "sub_ext_find_me"
            )
            assert result is not None
            assert result.id == sub.id


async def test_subscription_get_by_external_subscription_id_not_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            result = await repos.subscription.get_by_external_subscription_id(
                "sub_nope"
            )
            assert result is None


async def test_subscription_get_by_external_subscription_id_locked():
    async with TestSessionLocal() as session:
        async with session.begin():
            org_id = await _fresh_org(session)
            repos = RepositoryManager(session)
            free_price = await repos.plan_price.get_free_price()
            assert free_price is not None
            await repos.subscription.create(
                organization_id=org_id,
                plan_price_id=free_price.id,
                status="active",
                external_subscription_id="sub_ext_locked",
            )
            result = await repos.subscription.get_by_external_subscription_id_locked(
                "sub_ext_locked"
            )
            assert result is not None


async def test_subscription_get_stale_incomplete():
    async with TestSessionLocal() as session:
        async with session.begin():
            org_id = await _fresh_org(session)
            repos = RepositoryManager(session)
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
            results = await repos.subscription.get_stale_incomplete_subscriptions(
                threshold
            )
            assert any(s.id == stale_sub.id for s in results)


async def test_subscription_bulk_cancel_stale_incomplete():
    async with TestSessionLocal() as session:
        async with session.begin():
            org_id = await _fresh_org(session)
            repos = RepositoryManager(session)
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


async def test_subscription_acquire_checkout_lock():
    """pg_advisory_xact_lock is mocked to SELECT 1 by conftest fixture."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            # Should not raise
            await repos.subscription.acquire_checkout_lock(1)


async def test_subscription_create_or_get_active():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
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
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
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
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
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
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            count = await repos.plan_usage.get_count(
                organization_id=1,
                metric=_Metric.API_CALLS,
                period_start=date.today(),
            )
            assert count == 0


async def test_plan_usage_get_for_organization_empty():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            records = await repos.plan_usage.get_for_organization(
                organization_id=1,
                period_start=date.today(),
            )
            assert records == [] or len(records) == 0


# ---------------------------------------------------------------------------
# WebhookEventRepository
# ---------------------------------------------------------------------------


async def _create_webhook_event(
    session, external_event_id: str = "evt_test"
) -> WebhookEvent:
    repos = RepositoryManager(session)
    return await repos.webhook_event.create(
        external_event_id=external_event_id,
        event_type="customer.subscription.updated",
        status="received",
    )


async def test_webhook_event_get_by_external_event_id_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            event = await _create_webhook_event(session, "evt_find_me")
            repos = RepositoryManager(session)
            result = await repos.webhook_event.get_by_external_event_id("evt_find_me")
            assert result is not None
            assert result.id == event.id


async def test_webhook_event_get_by_external_event_id_not_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            result = await repos.webhook_event.get_by_external_event_id("evt_nope")
            assert result is None


async def test_webhook_event_mark_processed():
    async with TestSessionLocal() as session:
        async with session.begin():
            event = await _create_webhook_event(session, "evt_process_me")
            repos = RepositoryManager(session)
            updated = await repos.webhook_event.mark_processed(event)
            assert updated.status == "processed"
            assert updated.processed_at is not None


async def test_webhook_event_mark_failed():
    async with TestSessionLocal() as session:
        async with session.begin():
            event = await _create_webhook_event(session, "evt_fail_me")
            repos = RepositoryManager(session)
            updated = await repos.webhook_event.mark_failed(
                event, "something went wrong"
            )
            assert updated.status == "failed"
            assert updated.error == "something went wrong"
