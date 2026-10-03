"""Billing's test fixtures - a pytest plugin `tests.preload` registers while
billing is installed: billing's share of the seed (a free plan and every seeded
organization's billing account and free subscription), the mocked Stripe
provider, and a paid plan for tests that need one. Delete it with the module.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models.account import BillingAccount
from src.billing.models.billing import Plan, PlanPrice, Subscription
from src.billing.models.billing import PlanFeature as PlanFeatureModel
from src.billing.provider import (
    BillingProviderABC,
    CheckoutResult,
    CustomerPortalResult,
    ExternalPrice,
    ExternalProduct,
    ExternalSubscription,
    WebhookPayload,
    get_billing_provider,
)
from src.foundation.enums import PlanFeature
from src.foundation.models.organization import Organization
from src.init_db import INIT_AUTH_DATA
from src.main import app
from tests.conftest import TestSessionLocal


@pytest.fixture(autouse=True)
async def seed_billing(
    prepare_database: None,  # noqa: ARG001 - orders this after the foundation seed
) -> None:
    """Runs after the foundation seed (`prepare_database`)."""
    async with TestSessionLocal() as session, session.begin():
        organizations = list(
            (await session.execute(select(Organization).order_by(Organization.id)))
            .scalars()
            .all(),
        )
        await _seed(session, organizations)
    return


async def _seed(session: AsyncSession, organizations: list) -> None:
    # Seed free plan - local-only, no Stripe product/price IDs
    free_plan = Plan(
        name="Free",
        description="Free plan",
        external_product_id=None,
        is_active=True,
    )
    session.add(free_plan)
    await session.flush()
    free_price = PlanPrice(
        plan_id=free_plan.id,
        amount=0,
        currency="dkk",
        interval="month",
        interval_count=1,
        external_price_id=None,
        is_active=True,
    )
    session.add(free_price)
    await session.flush()
    session.add(PlanFeatureModel(plan_id=free_plan.id, feature=PlanFeature.API_TOKEN))
    await session.flush()

    # Seed a billing account and a free subscription for each test
    # organization, matching what billing's ORGANIZATION_CREATED handler does
    # in production. No Stripe customer is created at registration -
    # external_customer_id is set when the organization starts a trial or
    # paid checkout. Tests that need a paid subscription activate it via
    # checkout + webhook helpers (which will stamp the ID).
    for data, organization in zip(
        INIT_AUTH_DATA["organizations"],
        organizations,
        strict=True,
    ):
        session.add(
            BillingAccount(
                organization_id=organization.id,
                billing_email=data["owner"],
            ),
        )
        session.add(
            Subscription(
                organization_id=organization.id,
                plan_price_id=free_price.id,
                status="active",
            ),
        )


@pytest.fixture(autouse=True)
def mock_billing_provider(mocker):
    """Auto-used fixture that mocks the billing provider for all tests."""
    mock = mocker.MagicMock(spec=BillingProviderABC)

    mock.create_product.return_value = ExternalProduct(external_id="prod_test123")
    mock.update_product.return_value = ExternalProduct(external_id="prod_test123")
    mock.archive_product.return_value = None
    mock.create_price.return_value = ExternalPrice(external_id="price_test123")
    mock.archive_price.return_value = None
    _cus_ids = {1: "cus_test123", 2: "cus_test456"}
    mock.get_or_create_customer.side_effect = lambda *, organization_id, **_kwargs: (
        _cus_ids.get(organization_id, f"cus_{organization_id}")
    )
    mock.create_checkout_session.return_value = CheckoutResult(
        checkout_url="https://checkout.stripe.com/test_session",
        external_session_id="cs_test123",
    )
    mock.cancel_subscription.return_value = ExternalSubscription(
        external_subscription_id="sub_test123",
        external_customer_id="cus_test123",
        status="active",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=True,
        canceled_at=None,
        external_price_id="price_test123",
    )
    mock.resume_subscription.return_value = ExternalSubscription(
        external_subscription_id="sub_test123",
        external_customer_id="cus_test123",
        status="active",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=False,
        canceled_at=None,
        external_price_id="price_test123",
    )
    mock.switch_subscription_price.return_value = ExternalSubscription(
        external_subscription_id="sub_test123",
        external_customer_id="cus_test123",
        status="active",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=False,
        canceled_at=None,
        external_price_id="price_test456",
    )
    mock.has_payment_method.return_value = False
    mock.get_charge_customer.return_value = None
    mock.update_customer.return_value = None
    mock.get_customer_portal_url.return_value = CustomerPortalResult(
        portal_url="https://billing.stripe.com/portal/test",
    )
    mock.create_subscription.return_value = ExternalSubscription(
        external_subscription_id="sub_trial123",
        external_customer_id="cus_test123",
        status="trialing",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=False,
        canceled_at=None,
        external_price_id="price_test123",
    )
    mock.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_test123",
        event_type="subscription.updated",
        raw={},
    )

    app.dependency_overrides[get_billing_provider] = lambda: mock
    # Worker loops call the factory directly, outside FastAPI's DI.
    mocker.patch(
        "src.billing.services.maintenance.get_billing_provider",
        return_value=mock,
    )
    yield mock
    app.dependency_overrides.pop(get_billing_provider, None)


@pytest.fixture
async def plan_with_price() -> dict:
    """Create a plan with one price directly in the DB. Returns {"plan": ..., "price": ...}."""  # noqa: E501
    async with TestSessionLocal() as session:
        plan = Plan(
            name="Pro",
            description="Pro plan",
            external_product_id="prod_test123",
            is_active=True,
        )
        session.add(plan)
        await session.flush()
        plan_id = plan.id

        price = PlanPrice(
            plan_id=plan_id,
            amount=999,
            currency="dkk",
            interval="month",
            interval_count=1,
            external_price_id="price_test123",
            is_active=True,
        )
        session.add(price)
        await session.flush()
        price_id = price.id

        await session.commit()

    return {
        "plan": {
            "id": plan_id,
            "name": "Pro",
            "description": "Pro plan",
            "external_product_id": "prod_test123",
            "is_active": True,
        },
        "price": {
            "id": price_id,
            "plan_id": plan_id,
            "amount": 999,
            "currency": "dkk",
            "interval": "month",
            "interval_count": 1,
            "external_price_id": "price_test123",
            "is_active": True,
        },
    }
