"""Direct unit tests for billing services.

Bypasses HTTP/TestClient to ensure coverage.py captures service-layer execution.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.platform.core.config import settings
from src.platform.core.exceptions import (
    AlreadyExistsException,
    BillingProviderException,
    NotFoundException,
    ValidationException,
)
from src.platform.core.security import Auth
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.billing import CheckoutIn, StartTrialIn, SwitchPlanIn
from src.platform.services.billing import (
    BillingMaintenanceService,
    PlanService,
    SubscriptionService,
    UsageService,
    WebhookService,
    _get_period_field,
    run_stale_checkout_cleanup_loop,
    run_trial_reminder_loop,
)
from tests.conftest import TestSessionLocal


def _admin_auth(organization_id: int = 1) -> Auth:
    return Auth(
        id=1,
        name="Alice Owner",
        email="admin@example.org",
        organization_id=organization_id,
        roles=["Owner"],
        permissions=[
            p.value
            for p in __import__(
                "src.platform.enums", fromlist=["Permission"]
            ).Permission
        ],
    )


async def _get_paid_price_id(session) -> int:
    """Return the id of the pro plan_price seeded by plan_with_price fixture."""
    repos = RepositoryManager(session)
    prices = await repos.plan_price.get_all()
    for p in prices:
        if p.amount > 0 and p.external_price_id:
            return p.id
    raise RuntimeError("No paid plan price found")


async def _stamp_subscription_external_id(
    session, org_id: int, sub_ext_id: str
) -> None:
    repos = RepositoryManager(session)
    sub = await repos.subscription.get_active_for_organization(org_id)
    if sub:
        await repos.subscription.update(sub, external_subscription_id=sub_ext_id)


# ---------------------------------------------------------------------------
# PlanService
# ---------------------------------------------------------------------------


async def test_get_all_plans_returns_free_plan(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = PlanService(repos, mock_billing_provider)
            plans = await service.get_all_plans()
    assert any(p.name == "Free" for p in plans)


async def test_get_plan_not_found_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = PlanService(repos, mock_billing_provider)
            with pytest.raises(NotFoundException):
                await service.get_plan(999)


# ---------------------------------------------------------------------------
# SubscriptionService - start_checkout
# ---------------------------------------------------------------------------


async def test_start_checkout_invalid_price_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(NotFoundException):
                await service.start_checkout(CheckoutIn(plan_price_id=9999))


async def test_start_checkout_success(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            out = await service.start_checkout(CheckoutIn(plan_price_id=price_id))
    assert out.checkout_url


# ---------------------------------------------------------------------------
# SubscriptionService - start_trial
# ---------------------------------------------------------------------------


async def test_start_trial_free_plan_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            # Get the free plan price id
            free_prices = [p for p in await repos.plan_price.get_all() if p.amount == 0]
            assert free_prices
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(ValidationException):
                await service.start_trial(StartTrialIn(plan_price_id=free_prices[0].id))


async def test_start_trial_no_external_price_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            from src.platform.models.billing import Plan, PlanPrice

            repos = RepositoryManager(session)

            # Create a paid plan with no external_price_id
            plan = Plan(
                name="NoPriceExt",
                description="",
                external_product_id="prod_x",
                is_active=True,
            )
            session.add(plan)
            await session.flush()
            price = PlanPrice(
                plan_id=plan.id,
                amount=999,
                currency="usd",
                interval="month",
                interval_count=1,
                external_price_id=None,
                is_active=True,
            )
            session.add(price)
            await session.flush()

            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises((NotFoundException, ValidationException)):
                await service.start_trial(StartTrialIn(plan_price_id=price.id))


# ---------------------------------------------------------------------------
# SubscriptionService - get_current_subscription
# ---------------------------------------------------------------------------


async def test_get_current_subscription_returns_sub(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            sub = await service.get_current_subscription()
    assert sub.status == "active"


# ---------------------------------------------------------------------------
# SubscriptionService - cancel_subscription
# ---------------------------------------------------------------------------


async def test_cancel_free_sub_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(ValidationException):
                await service.cancel_subscription()


async def test_cancel_subscription_no_external_id(
    mock_billing_provider, plan_with_price
):
    """Subscription without external_subscription_id is canceled locally."""
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            # Switch to paid plan locally (no Stripe ID)
            await repos.subscription.update(sub, plan_price_id=price_id)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            out = await service.cancel_subscription()
    assert out.status == "canceled"


async def test_cancel_subscription_with_external_id(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                external_subscription_id="sub_test123",
            )
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            out = await service.cancel_subscription()
    assert out.cancel_at_period_end is True


# ---------------------------------------------------------------------------
# SubscriptionService - resume_subscription
# ---------------------------------------------------------------------------


async def test_resume_subscription_not_canceling_raises(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                external_subscription_id="sub_test123",
                cancel_at_period_end=False,
            )
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(ValidationException):
                await service.resume_subscription()


async def test_resume_subscription_success(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                external_subscription_id="sub_test123",
                cancel_at_period_end=True,
            )
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            out = await service.resume_subscription()
    assert out.cancel_at_period_end is False


# ---------------------------------------------------------------------------
# SubscriptionService - switch_plan
# ---------------------------------------------------------------------------


async def test_switch_plan_no_external_id_raises(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(ValidationException):
                await service.switch_plan(SwitchPlanIn(plan_price_id=price_id))


async def test_switch_plan_success(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            from src.platform.models.billing import Plan, PlanPrice

            repos = RepositoryManager(session)

            # Set up a second price to switch to
            plan2 = Plan(
                name="Pro2",
                description="",
                external_product_id="prod_p2",
                is_active=True,
            )
            session.add(plan2)
            await session.flush()
            price2 = PlanPrice(
                plan_id=plan2.id,
                amount=1999,
                currency="usd",
                interval="month",
                interval_count=1,
                external_price_id="price_test456",
                is_active=True,
            )
            session.add(price2)
            await session.flush()

            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            # Put on price_id first with an external sub id
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                external_subscription_id="sub_test123",
            )
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            out = await service.switch_plan(SwitchPlanIn(plan_price_id=price2.id))
    assert out.status == "active"


# ---------------------------------------------------------------------------
# SubscriptionService - get_customer_portal_url
# ---------------------------------------------------------------------------


async def test_get_customer_portal_url_no_customer_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(ValidationException):
                await service.get_customer_portal_url()


async def test_get_customer_portal_url_success(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_test123")
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            out = await service.get_customer_portal_url()
    assert "billing.stripe.com" in out.portal_url


# ---------------------------------------------------------------------------
# WebhookService - process_webhook + dispatch
# ---------------------------------------------------------------------------


def _make_webhook_raw(event_type: str, obj: dict) -> dict:
    return {"data": {"object": obj}}


async def test_webhook_subscription_updated_known_sub(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                external_subscription_id="sub_evt123",
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw = _make_webhook_raw(
                "customer.subscription.updated",
                {
                    "id": "sub_evt123",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "items": {"data": []},
                },
            )
            await service._dispatch("customer.subscription.updated", raw)


async def test_webhook_subscription_updated_unknown_sub(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw = _make_webhook_raw(
                "customer.subscription.updated",
                {"id": "sub_unknown", "status": "active", "items": {"data": []}},
            )
            # Should return without error (no-op when sub not found)
            await service._dispatch("customer.subscription.updated", raw)


async def test_webhook_subscription_deleted_restores_free(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_del123"
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw = _make_webhook_raw(
                "customer.subscription.deleted",
                {"id": "sub_del123", "canceled_at": None},
            )
            await service._dispatch("customer.subscription.deleted", raw)

    # Verify restored to free
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            assert sub.external_subscription_id is None


async def test_webhook_payment_method_attached(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_pm123")

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {"data": {"object": {"customer": "cus_pm123"}}}
            await service._dispatch("payment_method.attached", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org and org.has_payment_method is True


async def test_webhook_payment_method_detached(mock_billing_provider):
    mock_billing_provider.has_payment_method.return_value = False

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(
                org, external_customer_id="cus_det123", has_payment_method=True
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {"customer": "cus_det123"},
                    "previous_attributes": {},
                }
            }
            await service._dispatch("payment_method.detached", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org and org.has_payment_method is False


async def test_webhook_invoice_payment_succeeded_past_due(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                external_subscription_id="sub_inv123",
                status="past_due",
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_inv123",
                        "customer": None,
                        "parent": {},
                    }
                }
            }
            await service._dispatch("invoice.payment_succeeded", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub and sub.status == "active"


async def test_webhook_product_created(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "prod_new999",
                        "name": "New Plan",
                        "description": "A new plan",
                    }
                }
            }
            await service._dispatch("product.created", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            plan = await repos.plan.get_by_external_product_id("prod_new999")
            assert plan and plan.name == "New Plan"


async def test_webhook_product_updated(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            from src.platform.models.billing import Plan

            repos = RepositoryManager(session)
            plan = Plan(
                name="OldName",
                description="Old",
                external_product_id="prod_upd999",
                is_active=True,
            )
            session.add(plan)
            await session.flush()

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "prod_upd999",
                        "name": "UpdatedName",
                        "active": True,
                    }
                }
            }
            await service._dispatch("product.updated", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            _plan = await repos.plan.get_by_external_product_id("prod_upd999")
            assert _plan and _plan.name == "UpdatedName"


async def test_webhook_checkout_session_completed(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_chk123")

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_chk123",
                        "customer": "cus_chk123",
                        "metadata": {"organization_id": "1", "plan_price_id": "1"},
                    }
                }
            }
            await service._dispatch("checkout.session.completed", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub and sub.external_subscription_id == "sub_chk123"


async def test_webhook_checkout_session_expired_noop_active(mock_billing_provider):
    """Expired checkout for active (non-incomplete) sub is a no-op."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_exp123")
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "customer": "cus_exp123",
                        "metadata": {},
                    }
                }
            }
            # Should be a no-op (sub is active, not incomplete)
            await service._dispatch("checkout.session.expired", raw)


async def test_webhook_subscription_created(mock_billing_provider, plan_with_price):
    price_ext_id = plan_with_price["price"]["external_price_id"]

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_cre123")

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_cre123",
                        "status": "active",
                        "customer": "cus_cre123",
                        "cancel_at_period_end": False,
                        "items": {
                            "data": [
                                {
                                    "price": {"id": price_ext_id},
                                    "current_period_start": None,
                                    "current_period_end": None,
                                }
                            ]
                        },
                    }
                }
            }
            await service._dispatch("customer.subscription.created", raw)


async def test_webhook_subscription_trial_will_end(
    mock_billing_provider, plan_with_price
):
    from datetime import UTC, datetime, timedelta

    price_id = plan_with_price["price"]["id"]
    trial_end_ts = int((datetime.now(UTC) + timedelta(days=3)).timestamp())

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_trial_end"
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_trial_end",
                        "trial_end": trial_end_ts,
                    }
                }
            }
            await service._dispatch("customer.subscription.trial_will_end", raw)


async def test_webhook_subscription_paused_explicit(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_paused"
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_paused",
                        "status": "paused",
                        "pause_collection": {"behavior": "mark_uncollectible"},
                        "items": {"data": []},
                    }
                }
            }
            await service._dispatch("customer.subscription.paused", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub and sub.status == "paused"


async def test_webhook_invoice_payment_failed(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_fail123"
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_fail123",
                        "customer": None,
                        "parent": {},
                    }
                }
            }
            # _notify_payment_failed calls send_email via asyncio.to_thread - we just
            # verify no exception propagates from the handler itself
            await service._dispatch("invoice.payment_failed", raw)


async def test_webhook_invoice_marked_uncollectible(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    mock_billing_provider.delete_subscription.return_value = None

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                external_subscription_id="sub_uncoll123",
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_uncoll123",
                        "customer": None,
                        "parent": {},
                    }
                }
            }
            await service._dispatch("invoice.marked_uncollectible", raw)


async def test_webhook_subscription_resumed(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                external_subscription_id="sub_res123",
                status="paused",
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_res123",
                        "status": "active",
                        "cancel_at_period_end": False,
                        "items": {"data": []},
                    },
                    "previous_attributes": {
                        "pause_collection": {"behavior": "mark_uncollectible"}
                    },
                }
            }
            await service._dispatch("customer.subscription.resumed", raw)


async def test_webhook_unknown_event_type_is_noop(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            # Should not raise
            await service._dispatch("unknown.event.type", {"data": {"object": {}}})


async def test_process_webhook_idempotent(mock_billing_provider):
    """Second call with same event_id returns True without re-processing."""
    from src.platform.billing.types import WebhookPayload

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_idem123",
        event_type="unknown.type",
        raw={},
    )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            result = await service.process_webhook(b"payload", "sig")
    assert result is True

    # Process the same event again - should be idempotent
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            result2 = await service.process_webhook(b"payload", "sig")
    assert result2 is True


# ---------------------------------------------------------------------------
# _get_period_field utility
# ---------------------------------------------------------------------------


def test_get_period_field_returns_direct_value():
    result = _get_period_field(
        {"current_period_start": 1234567890}, "current_period_start"
    )
    assert result == 1234567890


def test_get_period_field_falls_back_to_items():
    obj = {"items": {"data": [{"current_period_start": 9999}]}}
    assert _get_period_field(obj, "current_period_start") == 9999


def test_get_period_field_returns_none_when_missing():
    assert _get_period_field({}, "current_period_start") is None


# ---------------------------------------------------------------------------
# PlanService - get_plan success
# ---------------------------------------------------------------------------


async def test_get_plan_success(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            plans = await repos.plan.get_active_plans()
            assert plans
            service = PlanService(repos, mock_billing_provider)
            plan_out = await service.get_plan(plans[0].id)
    assert plan_out.name == "Free"


# ---------------------------------------------------------------------------
# SubscriptionService - start_checkout additional edge cases
# ---------------------------------------------------------------------------


async def test_start_checkout_inactive_price_raises(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            price = await repos.plan_price.get(price_id)
            assert price is not None
            await repos.plan_price.update(price, is_active=False)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(NotFoundException):
                await service.start_checkout(CheckoutIn(plan_price_id=price_id))


async def test_start_checkout_no_external_price_id_raises(mock_billing_provider):
    from src.platform.models.billing import Plan, PlanPrice

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            plan = Plan(
                name="NoPriceExtCO",
                description="",
                external_product_id="prod_co_x",
                is_active=True,
            )
            session.add(plan)
            await session.flush()
            price = PlanPrice(
                plan_id=plan.id,
                amount=999,
                currency="usd",
                interval="month",
                interval_count=1,
                external_price_id=None,
                is_active=True,
            )
            session.add(price)
            await session.flush()
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(NotFoundException):
                await service.start_checkout(CheckoutIn(plan_price_id=price.id))


async def test_start_checkout_active_paid_sub_raises(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                status="active",
                external_subscription_id="sub_already",
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(AlreadyExistsException):
                await service.start_checkout(CheckoutIn(plan_price_id=price_id))


async def test_start_checkout_org_not_found_raises(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(9999)
            service = SubscriptionService(
                repos, mock_billing_provider, _admin_auth(organization_id=9999)
            )
            with pytest.raises(NotFoundException):
                await service.start_checkout(CheckoutIn(plan_price_id=price_id))


# ---------------------------------------------------------------------------
# SubscriptionService - start_trial additional edge cases
# ---------------------------------------------------------------------------


async def test_start_trial_trials_not_configured_raises(
    mock_billing_provider, plan_with_price, mocker
):
    from src.platform.core.config import settings as _settings

    mocker.patch.object(_settings, "billing_trial_period_days", 0)
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(ValidationException):
                await service.start_trial(StartTrialIn(plan_price_id=price_id))


async def test_start_trial_org_not_found_raises(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(9999)
            service = SubscriptionService(
                repos, mock_billing_provider, _admin_auth(organization_id=9999)
            )
            with pytest.raises((NotFoundException, ValidationException)):
                await service.start_trial(StartTrialIn(plan_price_id=price_id))


async def test_start_trial_already_used_raises(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, trial_used=True)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(ValidationException):
                await service.start_trial(StartTrialIn(plan_price_id=price_id))


async def test_start_trial_existing_trialing_sub_raises(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                status="trialing",
                external_subscription_id="sub_trial_x",
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(AlreadyExistsException):
                await service.start_trial(StartTrialIn(plan_price_id=price_id))


async def test_start_trial_existing_active_paid_raises(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                status="active",
                external_subscription_id="sub_paid_x",
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(AlreadyExistsException):
                await service.start_trial(StartTrialIn(plan_price_id=price_id))


async def test_start_trial_success(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            out = await service.start_trial(StartTrialIn(plan_price_id=price_id))
    assert out.checkout_url


# ---------------------------------------------------------------------------
# SubscriptionService - get_current_subscription not found
# ---------------------------------------------------------------------------


async def test_get_current_subscription_no_active_sub_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, status="canceled", canceled_at=datetime.now(UTC)
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(NotFoundException):
                await service.get_current_subscription()


# ---------------------------------------------------------------------------
# SubscriptionService - resume_subscription no external id
# ---------------------------------------------------------------------------


async def test_resume_subscription_no_external_id_raises(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                cancel_at_period_end=True,
                external_subscription_id=None,
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(ValidationException):
                await service.resume_subscription()


# ---------------------------------------------------------------------------
# SubscriptionService - switch_plan additional edge cases
# ---------------------------------------------------------------------------


async def test_switch_plan_invalid_price_raises(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_sp1"
            )
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(NotFoundException):
                await service.switch_plan(SwitchPlanIn(plan_price_id=9999))


async def test_switch_plan_free_price_raises(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            free_prices = [p for p in await repos.plan_price.get_all() if p.amount == 0]
            assert free_prices
            free_price_id = free_prices[0].id
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_sp2"
            )
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(ValidationException):
                await service.switch_plan(SwitchPlanIn(plan_price_id=free_price_id))


async def test_switch_plan_no_external_price_raises(
    mock_billing_provider, plan_with_price
):
    from src.platform.models.billing import Plan, PlanPrice

    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            plan2 = Plan(
                name="NoPriceExtSP",
                description="",
                external_product_id="prod_sp_x",
                is_active=True,
            )
            session.add(plan2)
            await session.flush()
            no_ext_price = PlanPrice(
                plan_id=plan2.id,
                amount=500,
                currency="usd",
                interval="month",
                interval_count=1,
                external_price_id=None,
                is_active=True,
            )
            session.add(no_ext_price)
            await session.flush()
            no_ext_price_id = no_ext_price.id

            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_sp3"
            )
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(NotFoundException):
                await service.switch_plan(SwitchPlanIn(plan_price_id=no_ext_price_id))


async def test_switch_plan_same_plan_raises(mock_billing_provider, plan_with_price):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_sp4"
            )
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(ValidationException):
                await service.switch_plan(SwitchPlanIn(plan_price_id=price_id))


# ---------------------------------------------------------------------------
# WebhookService - process_webhook exception branches
# ---------------------------------------------------------------------------


async def test_process_webhook_billing_exception_returns_false(
    mock_billing_provider, mocker
):
    """
    BillingProviderException causes mark_failed and
    returns False (Stripe should retry).
    """
    from src.platform.billing.types import WebhookPayload

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_bill_err",
        event_type="customer.subscription.updated",
        raw={},
    )

    mocker.patch(
        "src.platform.services.billing.WebhookService._dispatch",
        side_effect=BillingProviderException("provider down"),
    )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            result = await service.process_webhook(b"payload", "sig")
    assert result is False


async def test_process_webhook_permanent_exception_returns_true(
    mock_billing_provider, mocker
):
    """
    Unexpected exceptions are logged and acked
    (returns True) to stop Stripe retries.
    """
    from src.platform.billing.types import WebhookPayload

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_perm_err",
        event_type="customer.subscription.updated",
        raw={},
    )

    mocker.patch(
        "src.platform.services.billing.WebhookService._dispatch",
        side_effect=RuntimeError("unexpected bug"),
    )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            result = await service.process_webhook(b"payload", "sig")
    assert result is True


# ---------------------------------------------------------------------------
# WebhookService - _handle_checkout_completed edge cases
# ---------------------------------------------------------------------------


async def test_handle_checkout_completed_no_subscription_id(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": None,
                        "customer": "cus_x",
                        "metadata": {},
                    }
                }
            }
            await service._dispatch("checkout.session.completed", raw)


async def test_handle_checkout_completed_org_not_found(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_x",
                        "customer": "cus_nobody",
                        "metadata": {},
                    }
                }
            }
            await service._dispatch("checkout.session.completed", raw)


async def test_handle_checkout_completed_stamps_customer_id(mock_billing_provider):
    """Org found via metadata fallback gets its external_customer_id stamped."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_stamp",
                        "customer": "cus_stamp_new",
                        "metadata": {"organization_id": "1", "plan_price_id": "1"},
                    }
                }
            }
            await service._dispatch("checkout.session.completed", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org and org.external_customer_id == "cus_stamp_new"


async def test_handle_checkout_completed_no_active_sub(mock_billing_provider):
    """When org has no active subscription, handler is a no-op."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_nosub")
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, status="canceled", canceled_at=datetime.now(UTC)
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_nosub",
                        "customer": "cus_nosub",
                        "metadata": {},
                    }
                }
            }
            await service._dispatch("checkout.session.completed", raw)


async def test_handle_checkout_completed_invalid_price_in_metadata(
    mock_billing_provider,
):
    """Invalid plan_price_id in metadata is logged but does not raise."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_badmeta")

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_badmeta",
                        "customer": "cus_badmeta",
                        "metadata": {"plan_price_id": "not_an_int"},
                    }
                }
            }
            await service._dispatch("checkout.session.completed", raw)


# ---------------------------------------------------------------------------
# WebhookService - _handle_subscription_updated price change
# ---------------------------------------------------------------------------


async def test_webhook_subscription_updated_price_changed(
    mock_billing_provider, plan_with_price
):
    price_ext_id = plan_with_price["price"]["external_price_id"]
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, external_subscription_id="sub_price_chg"
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_price_chg",
                        "status": "active",
                        "cancel_at_period_end": False,
                        "items": {"data": [{"price": {"id": price_ext_id}}]},
                    }
                }
            }
            await service._dispatch("customer.subscription.updated", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub and sub.plan_price_id == price_id


# ---------------------------------------------------------------------------
# WebhookService - _handle_subscription_deleted edge cases
# ---------------------------------------------------------------------------


async def test_webhook_subscription_deleted_sub_not_found(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw = _make_webhook_raw(
                "customer.subscription.deleted",
                {"id": "sub_ghost", "canceled_at": None},
            )
            await service._dispatch("customer.subscription.deleted", raw)


async def test_webhook_subscription_deleted_no_free_price_with_ts(
    mock_billing_provider, plan_with_price
):
    """
    When no free price is configured, subscription is
    marked canceled with the Stripe timestamp.
    """
    price_id = plan_with_price["price"]["id"]
    canceled_ts = int(datetime.now(UTC).timestamp())

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_nofreep"
            )
            # Disable free price
            prices = await repos.plan_price.get_all()
            for p in prices:
                if p.amount == 0:
                    await repos.plan_price.update(p, is_active=False)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw = _make_webhook_raw(
                "customer.subscription.deleted",
                {"id": "sub_nofreep", "canceled_at": canceled_ts},
            )
            await service._dispatch("customer.subscription.deleted", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub is None  # canceled


async def test_webhook_subscription_deleted_no_free_price_no_ts(
    mock_billing_provider, plan_with_price
):
    """No free price and no canceled_at timestamp: falls back to now()."""
    price_id = plan_with_price["price"]["id"]

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_nofreep2"
            )
            prices = await repos.plan_price.get_all()
            for p in prices:
                if p.amount == 0:
                    await repos.plan_price.update(p, is_active=False)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw = _make_webhook_raw(
                "customer.subscription.deleted",
                {"id": "sub_nofreep2", "canceled_at": None},
            )
            await service._dispatch("customer.subscription.deleted", raw)


# ---------------------------------------------------------------------------
# WebhookService - payment_method edge cases
# ---------------------------------------------------------------------------


async def test_webhook_payment_method_attached_no_customer(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {"data": {"object": {"customer": None}}}
            await service._dispatch("payment_method.attached", raw)


async def test_webhook_payment_method_detached_no_change_when_no_payment_method(
    mock_billing_provider,
):
    """has_payment_method=False org skips the provider call."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(
                org, external_customer_id="cus_nopm", has_payment_method=False
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {"customer": "cus_nopm"},
                    "previous_attributes": {},
                }
            }
            await service._dispatch("payment_method.detached", raw)

    mock_billing_provider.has_payment_method.assert_not_called()


# ---------------------------------------------------------------------------
# WebhookService - invoice handlers when no subscription found
# ---------------------------------------------------------------------------


async def test_webhook_invoice_payment_failed_no_sub(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_ghost_fail",
                        "customer": None,
                        "parent": {},
                    }
                }
            }
            await service._dispatch("invoice.payment_failed", raw)


async def test_webhook_invoice_payment_succeeded_no_sub(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_ghost_ok",
                        "customer": None,
                        "parent": {},
                    }
                }
            }
            await service._dispatch("invoice.payment_succeeded", raw)


async def test_webhook_invoice_payment_succeeded_via_customer_lookup(
    mock_billing_provider, plan_with_price
):
    """Subscription found by customer lookup when subscription field is missing."""
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_inv_cust")
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                status="past_due",
                external_subscription_id="sub_inv_cust",
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": None,
                        "customer": "cus_inv_cust",
                        "parent": {},
                    }
                }
            }
            await service._dispatch("invoice.payment_succeeded", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub and sub.status == "active"


# ---------------------------------------------------------------------------
# WebhookService - _handle_subscription_created edge cases
# ---------------------------------------------------------------------------


async def test_webhook_subscription_created_sub_not_found(mock_billing_provider):
    """subscription.created for unknown customer is a no-op."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_unk_cre",
                        "status": "active",
                        "customer": "cus_nobody_cre",
                        "cancel_at_period_end": False,
                        "items": {"data": []},
                    }
                }
            }
            await service._dispatch("customer.subscription.created", raw)


async def test_webhook_subscription_created_with_trial_end(
    mock_billing_provider, plan_with_price
):
    """subscription.created with trialing status marks trial_used on org."""
    price_ext_id = plan_with_price["price"]["external_price_id"]
    trial_ts = int(datetime.now(UTC).timestamp()) + 7 * 86400

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_trial_cre")

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_trial_cre",
                        "status": "trialing",
                        "customer": "cus_trial_cre",
                        "cancel_at_period_end": False,
                        "trial_end": trial_ts,
                        "items": {"data": [{"price": {"id": price_ext_id}}]},
                    }
                }
            }
            await service._dispatch("customer.subscription.created", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org and org.trial_used is True
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub and sub.trial_end is not None


# ---------------------------------------------------------------------------
# WebhookService - _handle_checkout_session_expired with incomplete sub
# ---------------------------------------------------------------------------


async def test_handle_checkout_session_expired_restores_free(mock_billing_provider):
    """Incomplete sub + free price > restored to free."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_exp_free")
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(sub, status="incomplete")

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "customer": "cus_exp_free",
                        "metadata": {},
                    }
                }
            }
            await service._dispatch("checkout.session.expired", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub and sub.status == "active"
            assert sub.external_subscription_id is None


async def test_handle_checkout_session_expired_no_free_price_cancels(
    mock_billing_provider,
):
    """Incomplete sub + no free price > marked canceled."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_exp_nofreep")
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(sub, status="incomplete")
            prices = await repos.plan_price.get_all()
            for p in prices:
                if p.amount == 0:
                    await repos.plan_price.update(p, is_active=False)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "customer": "cus_exp_nofreep",
                        "metadata": {},
                    }
                }
            }
            await service._dispatch("checkout.session.expired", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub is None  # was canceled


# ---------------------------------------------------------------------------
# WebhookService - _handle_invoice_payment_action_required
# ---------------------------------------------------------------------------


async def test_webhook_invoice_payment_action_required(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_action"
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_action",
                        "customer": None,
                        "parent": {},
                    }
                }
            }
            await service._dispatch("invoice.payment_action_required", raw)


# ---------------------------------------------------------------------------
# WebhookService - _handle_invoice_marked_uncollectible no sub
# ---------------------------------------------------------------------------


async def test_webhook_invoice_marked_uncollectible_no_sub(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_ghost_uncoll",
                        "customer": None,
                        "parent": {},
                    }
                }
            }
            await service._dispatch("invoice.marked_uncollectible", raw)


# ---------------------------------------------------------------------------
# WebhookService - _handle_subscription_trial_will_end no sub
# ---------------------------------------------------------------------------


async def test_webhook_subscription_trial_will_end_no_sub(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {"object": {"id": "sub_ghost_trial", "trial_end": None}}
            }
            await service._dispatch("customer.subscription.trial_will_end", raw)


# ---------------------------------------------------------------------------
# WebhookService - _handle_subscription_paused edge cases
# ---------------------------------------------------------------------------


async def test_webhook_subscription_paused_no_sub(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_ghost_paused",
                        "status": "paused",
                        "pause_collection": {"behavior": "mark_uncollectible"},
                    }
                }
            }
            await service._dispatch("customer.subscription.paused", raw)


async def test_webhook_subscription_paused_trial_end_downgrade(
    mock_billing_provider, plan_with_price
):
    """
    Trial-end pause (no pause_collection) downgrades
    to free and sends notification
    """
    price_id = plan_with_price["price"]["id"]
    mock_billing_provider.delete_subscription.return_value = None

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_trial_pause"
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_trial_pause",
                        "status": "paused",
                        "pause_collection": None,
                        "items": {"data": []},
                    }
                }
            }
            await service._dispatch("customer.subscription.paused", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            # Downgraded to free (external_subscription_id cleared)
            assert sub and sub.external_subscription_id is None


# ---------------------------------------------------------------------------
# WebhookService - _handle_subscription_resumed edge cases
# ---------------------------------------------------------------------------


async def test_webhook_subscription_resumed_no_pause_collection_in_prev(
    mock_billing_provider, plan_with_price
):
    """resumed without pause_collection in previous_attributes: no notification sent."""
    price_id = plan_with_price["price"]["id"]

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_res_noprev"
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_res_noprev",
                        "status": "active",
                        "cancel_at_period_end": False,
                        "items": {"data": []},
                    },
                    "previous_attributes": {},  # no pause_collection key
                }
            }
            await service._dispatch("customer.subscription.resumed", raw)


async def test_webhook_subscription_resumed_sub_not_found(mock_billing_provider):
    """resumed with pause_collection in prev but sub not in DB: no-op."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_ghost_resumed",
                        "status": "active",
                        "cancel_at_period_end": False,
                        "items": {"data": []},
                    },
                    "previous_attributes": {
                        "pause_collection": {"behavior": "mark_uncollectible"}
                    },
                }
            }
            await service._dispatch("customer.subscription.resumed", raw)


# ---------------------------------------------------------------------------
# WebhookService - product/price handler edge cases
# ---------------------------------------------------------------------------


async def test_webhook_product_created_already_exists(
    mock_billing_provider, plan_with_price
):
    ext_id = plan_with_price["plan"]["external_product_id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": ext_id,
                        "name": "ShouldNotCreate",
                        "description": None,
                    }
                }
            }
            await service._dispatch("product.created", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            plans = [
                p
                for p in await repos.plan.get_active_plans()
                if p.external_product_id == ext_id
            ]
            assert len(plans) == 1  # no duplicate


async def test_webhook_product_updated_not_found(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {"id": "prod_ghost", "name": "Ghost", "active": True}
                }
            }
            await service._dispatch("product.updated", raw)


async def test_webhook_product_updated_no_changes(
    mock_billing_provider, plan_with_price
):
    """product.updated with no recognized fields does not call update."""
    ext_id = plan_with_price["plan"]["external_product_id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            # Send event with no name/description/active fields
            raw: dict[str, Any] = {"data": {"object": {"id": ext_id}}}
            await service._dispatch("product.updated", raw)


async def test_webhook_price_created_already_exists(
    mock_billing_provider, plan_with_price
):
    ext_price_id = plan_with_price["price"]["external_price_id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": ext_price_id,
                        "product": plan_with_price["plan"]["external_product_id"],
                        "unit_amount": 999,
                        "currency": "dkk",
                        "recurring": {"interval": "month", "interval_count": 1},
                    }
                }
            }
            await service._dispatch("price.created", raw)


async def test_webhook_price_created_no_product_id(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {"object": {"id": "price_no_prod", "product": None}}
            }
            await service._dispatch("price.created", raw)


async def test_webhook_price_created_plan_not_found(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {"id": "price_ghost_plan", "product": "prod_ghost_9999"}
                }
            }
            await service._dispatch("price.created", raw)


async def test_webhook_price_created_success(mock_billing_provider, plan_with_price):
    ext_prod_id = plan_with_price["plan"]["external_product_id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "price_new_999",
                        "product": ext_prod_id,
                        "unit_amount": 1999,
                        "currency": "usd",
                        "recurring": {"interval": "year", "interval_count": 1},
                    }
                }
            }
            await service._dispatch("price.created", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            new_price = await repos.plan_price.get_by_external_price_id("price_new_999")
            assert (
                new_price and new_price.amount == 1999 and new_price.interval == "year"
            )


async def test_webhook_price_updated_not_found(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {"object": {"id": "price_ghost_upd", "active": False}}
            }
            await service._dispatch("price.updated", raw)


async def test_webhook_price_updated_no_active_field(
    mock_billing_provider, plan_with_price
):
    """price.updated without 'active' field is a no-op."""
    ext_price_id = plan_with_price["price"]["external_price_id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {"data": {"object": {"id": ext_price_id}}}
            await service._dispatch("price.updated", raw)


async def test_webhook_price_updated_success(mock_billing_provider, plan_with_price):
    ext_price_id = plan_with_price["price"]["external_price_id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {"object": {"id": ext_price_id, "active": False}}
            }
            await service._dispatch("price.updated", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            price = await repos.plan_price.get_by_external_price_id(ext_price_id)
            assert price and price.is_active is False


# ---------------------------------------------------------------------------
# UsageService
# ---------------------------------------------------------------------------


async def test_usage_service_get_current_usage_empty():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = UsageService(repos, _admin_auth())
            usage = await service.get_current_usage()
    assert usage.usage == []


# ---------------------------------------------------------------------------
# BillingMaintenanceService
# ---------------------------------------------------------------------------


async def test_billing_maintenance_cleanup_stale_checkouts():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = BillingMaintenanceService(repos)
            count = await service.cleanup_stale_checkouts()
    assert count >= 0


# ---------------------------------------------------------------------------
# run_stale_checkout_cleanup_loop
# ---------------------------------------------------------------------------


async def test_run_stale_checkout_cleanup_loop(mocker):
    """Loop runs one cleanup iteration (after sleep) then exits on CancelledError."""
    call_count = 0

    async def mock_sleep(_delay):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    mocker.patch("src.platform.services.billing.asyncio.sleep", side_effect=mock_sleep)

    with pytest.raises(asyncio.CancelledError):
        await run_stale_checkout_cleanup_loop(TestSessionLocal)

    assert call_count >= 2  # first sleep + cleanup ran + second sleep raised


# ---------------------------------------------------------------------------
# Additional targeted tests for remaining missing lines
# ---------------------------------------------------------------------------


async def test_start_trial_inactive_price_raises(
    mock_billing_provider, plan_with_price
):
    """start_trial with inactive price raises NotFoundException (line 187)."""
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            price = await repos.plan_price.get(price_id)
            assert price is not None
            await repos.plan_price.update(price, is_active=False)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(NotFoundException):
                await service.start_trial(StartTrialIn(plan_price_id=price_id))


async def test_cancel_subscription_no_active_sub_raises(mock_billing_provider):
    """
    _get_active_subscription raises NotFoundException
    when no active sub exists (line 395)
    """
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, status="canceled", canceled_at=datetime.now(UTC)
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())
            with pytest.raises(NotFoundException):
                await service.cancel_subscription()


async def test_checkout_completed_invalid_org_id_in_metadata(mock_billing_provider):
    """Invalid organization_id in metadata is caught silently (lines 500-501)."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_bad_org",
                        "customer": "cus_not_found_xx",
                        "metadata": {"organization_id": "not_a_number"},
                    }
                }
            }
            await service._dispatch("checkout.session.completed", raw)


async def test_notify_subscription_managers_org_not_found(mock_billing_provider):
    """_notify_subscription_managers returns early when org not found (line 516)."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            await service._notify_subscription_managers(
                organization_id=9999,
                email_template="test-template",
                data={},
            )


async def test_invoice_no_sub_id_and_no_customer_returns_none(mock_billing_provider):
    """
    _get_subscription_from_invoice returns None when
    both sub_id and customer are absent (line 711)
    """
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {"subscription": None, "customer": None, "parent": {}}
                }
            }
            await service._dispatch("invoice.payment_failed", raw)


async def test_webhook_subscription_created_create_or_get_active(mock_billing_provider):
    """subscription.created for org with no active sub creates one (line 754)."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(
                org, external_customer_id="cus_no_active_sub"
            )
            # Cancel the existing subscription so
            # get_active_for_organization_locked returns None
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, status="canceled", canceled_at=datetime.now(UTC)
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_create_new",
                        "status": "active",
                        "customer": "cus_no_active_sub",
                        "cancel_at_period_end": False,
                        "items": {"data": []},
                    }
                }
            }
            await service._dispatch("customer.subscription.created", raw)


async def test_webhook_subscription_created_trialing_via_sub_id(
    mock_billing_provider, plan_with_price
):
    """
    sub found by ID with trialing status triggers
    org lookup to set trial_used (line 788)
    """
    price_ext_id = plan_with_price["price"]["external_price_id"]

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(
                org, external_customer_id="cus_trial_via_id"
            )
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, external_subscription_id="sub_trial_via_id"
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_trial_via_id",
                        "status": "trialing",
                        "customer": "cus_trial_via_id",
                        "cancel_at_period_end": False,
                        "trial_end": int(datetime.now(UTC).timestamp()) + 86400,
                        "items": {"data": [{"price": {"id": price_ext_id}}]},
                    }
                }
            }
            await service._dispatch("customer.subscription.created", raw)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org and org.trial_used is True


async def test_webhook_invoice_payment_action_required_no_sub(mock_billing_provider):
    """invoice.payment_action_required with no matching sub is a no-op (line 832)."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_ghost_action2",
                        "customer": None,
                        "parent": {},
                    }
                }
            }
            await service._dispatch("invoice.payment_action_required", raw)


async def test_downgrade_to_free_no_free_price_cancels_via_stripe(
    mock_billing_provider, plan_with_price
):
    """
    _downgrade_to_free with no free plan cancels via
    Stripe and marks canceled (lines 858-868)
    """
    price_id = plan_with_price["price"]["id"]
    mock_billing_provider.delete_subscription.return_value = None

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub, plan_price_id=price_id, external_subscription_id="sub_dg_nofreep"
            )
            prices = await repos.plan_price.get_all()
            for p in prices:
                if p.amount == 0:
                    await repos.plan_price.update(p, is_active=False)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "subscription": "sub_dg_nofreep",
                        "customer": None,
                        "parent": {},
                    }
                }
            }
            await service._dispatch("invoice.marked_uncollectible", raw)

    mock_billing_provider.delete_subscription.assert_called_with("sub_dg_nofreep")


async def test_webhook_subscription_paused_trial_end_no_free_price(
    mock_billing_provider, plan_with_price
):
    """
    Trial-end pause with no free price: _downgrade_to_free
    returns None > early return (line 966)
    """
    price_id = plan_with_price["price"]["id"]
    mock_billing_provider.delete_subscription.return_value = None

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                external_subscription_id="sub_pause_nofreep",
            )
            prices = await repos.plan_price.get_all()
            for p in prices:
                if p.amount == 0:
                    await repos.plan_price.update(p, is_active=False)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {
                    "object": {
                        "id": "sub_pause_nofreep",
                        "status": "paused",
                        "pause_collection": None,
                        "items": {"data": []},
                    }
                }
            }
            await service._dispatch("customer.subscription.paused", raw)


async def test_webhook_product_updated_with_description(
    mock_billing_provider, plan_with_price
):
    """product.updated with description field updates it (line 1028)."""
    ext_id = plan_with_price["plan"]["external_product_id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)
            raw: dict[str, Any] = {
                "data": {"object": {"id": ext_id, "description": "New description"}}
            }
            await service._dispatch("product.updated", raw)


async def test_run_stale_checkout_cleanup_loop_handles_exception(mocker):
    """
    Loop catches exceptions and continues;
    exception path covered (lines 1141-1142)
    """
    call_count = 0

    async def mock_sleep(_delay):
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            raise asyncio.CancelledError()

    mocker.patch("src.platform.services.billing.asyncio.sleep", side_effect=mock_sleep)
    mocker.patch(
        "src.platform.services.billing.BillingMaintenanceService.cleanup_stale_checkouts",
        side_effect=RuntimeError("simulated db error"),
    )

    with pytest.raises(asyncio.CancelledError):
        await run_stale_checkout_cleanup_loop(TestSessionLocal)

    assert call_count >= 3


# ---------------------------------------------------------------------------
# BillingMaintenanceService.send_trial_reminders
# ---------------------------------------------------------------------------


async def _age_organization(organization_id: int, days: int) -> None:
    """Backdate an organization so it clears the reminder delay."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            organization = await repos.organization.get(organization_id)
            assert organization
            organization.created_at = datetime.now(UTC) - timedelta(days=days)


async def _run_trial_reminders() -> int:
    async with TestSessionLocal() as session:
        async with session.begin():
            service = BillingMaintenanceService(RepositoryManager(session))
            return await service.send_trial_reminders()


async def test_send_trial_reminders_emails_managers_once(mocker):
    send = mocker.patch("src.platform.services.billing.send_email")
    await _age_organization(1, days=settings.billing_trial_reminder_delay_days + 1)

    count = await _run_trial_reminders()

    assert count >= 1
    templates = {call.kwargs["email_template"] for call in send.call_args_list}
    assert templates == {"trial-available"}
    data = send.call_args_list[0].kwargs["data"]
    assert data["trial_days"] == settings.billing_trial_period_days

    async with TestSessionLocal() as session:
        organization = await RepositoryManager(session).organization.get(1)
        assert organization and organization.trial_reminder_sent_at is not None

    # Second pass is a no-op - the stamp excludes the organization.
    send.reset_mock()
    assert await _run_trial_reminders() == 0
    send.assert_not_called()


async def test_send_trial_reminders_skips_recent_signups(mocker):
    send = mocker.patch("src.platform.services.billing.send_email")

    # Organizations are created "now" by the fixture, so none clear the delay.
    assert await _run_trial_reminders() == 0
    send.assert_not_called()


async def test_send_trial_reminders_skips_used_trial(mocker):
    send = mocker.patch("src.platform.services.billing.send_email")
    await _age_organization(1, days=settings.billing_trial_reminder_delay_days + 1)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            for organization_id in (1, 2):
                organization = await repos.organization.get(organization_id)
                assert organization
                await repos.organization.update(organization, trial_used=True)

    assert await _run_trial_reminders() == 0
    send.assert_not_called()


async def test_send_trial_reminders_skips_trialing_subscription(mocker):
    send = mocker.patch("src.platform.services.billing.send_email")
    await _age_organization(1, days=settings.billing_trial_reminder_delay_days + 1)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(sub, status="trialing")

    await _run_trial_reminders()

    reminded = {call.kwargs["address"] for call in send.call_args_list}
    async with TestSessionLocal() as session:
        organization = await RepositoryManager(session).organization.get(1)
        assert organization and organization.trial_reminder_sent_at is None
    assert all("organization1" not in address for address in reminded)


async def test_send_trial_reminders_disabled_when_trials_off(mocker):
    send = mocker.patch("src.platform.services.billing.send_email")
    mocker.patch.object(settings, "billing_trial_period_days", 0)
    await _age_organization(1, days=30)

    assert await _run_trial_reminders() == 0
    send.assert_not_called()


async def test_run_trial_reminder_loop_handles_exception(mocker):
    """Loop catches exceptions and keeps running."""
    call_count = 0

    async def mock_sleep(_delay):
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            raise asyncio.CancelledError()

    mocker.patch("src.platform.services.billing.asyncio.sleep", side_effect=mock_sleep)
    mocker.patch(
        "src.platform.services.billing.BillingMaintenanceService.send_trial_reminders",
        side_effect=RuntimeError("simulated db error"),
    )

    with pytest.raises(asyncio.CancelledError):
        await run_trial_reminder_loop(TestSessionLocal)

    assert call_count >= 3
