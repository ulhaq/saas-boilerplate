"""Unit tests for StripeProvider - mock the stripe SDK directly."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe

from src.platform.billing.stripe_provider import StripeProvider
from src.platform.billing.types import (
    CheckoutResult,
    CustomerPortalResult,
    ExternalPrice,
    ExternalProduct,
    ExternalSubscription,
)
from src.platform.core.exceptions import (
    BillingProviderException,
    BillingWebhookException,
)

API_KEY = "sk_test_fake"
WEBHOOK_SECRET = "whsec_fake"


def _provider() -> StripeProvider:
    return StripeProvider(api_key=API_KEY, webhook_secret=WEBHOOK_SECRET)


def _fake_sub(
    sub_id: str = "sub_123",
    cus_id: str = "cus_123",
    price_id: str = "price_123",
    status: str = "active",
    cancel_at_period_end: bool = False,
    canceled_at: int | None = None,
    cancel_at: int | None = None,
    trial_end: int | None = None,
) -> MagicMock:
    item = MagicMock()
    item.price.id = price_id
    item.current_period_start = 1700000000
    item.current_period_end = 1702000000

    sub = MagicMock()
    sub.id = sub_id
    sub.customer = cus_id
    sub.status = status
    sub.cancel_at_period_end = cancel_at_period_end
    sub.canceled_at = canceled_at
    sub.cancel_at = cancel_at
    sub.trial_end = trial_end
    sub.items.data = [item]
    return sub


# ---------------------------------------------------------------------------
# search_product_by_name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_product_by_name_found():
    fake_product = MagicMock()
    fake_product.id = "prod_existing"
    search_result = MagicMock()
    search_result.data = [fake_product]

    with patch.object(
        stripe.Product, "search_async", new=AsyncMock(return_value=search_result)
    ):
        result = await _provider().search_product_by_name("Pro Plan")

    assert isinstance(result, ExternalProduct)
    assert result.external_id == "prod_existing"


@pytest.mark.asyncio
async def test_search_product_by_name_not_found():
    search_result = MagicMock()
    search_result.data = []

    with patch.object(
        stripe.Product, "search_async", new=AsyncMock(return_value=search_result)
    ):
        result = await _provider().search_product_by_name("Ghost Plan")

    assert result is None


@pytest.mark.asyncio
async def test_search_product_by_name_escapes_single_quote():
    """Names containing single quotes must be escaped in the Stripe query."""
    search_result = MagicMock()
    search_result.data = []

    with patch.object(
        stripe.Product, "search_async", new=AsyncMock(return_value=search_result)
    ) as mock_search:
        await _provider().search_product_by_name("O'Brien Plan")

    query: str = mock_search.call_args[1]["query"]
    assert "O\\'Brien" in query


@pytest.mark.asyncio
async def test_search_product_by_name_stripe_error_raises():
    with patch.object(
        stripe.Product,
        "search_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().search_product_by_name("Any Plan")


# ---------------------------------------------------------------------------
# create_product
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_product_success():
    fake_product = MagicMock()
    fake_product.id = "prod_new"

    with patch.object(
        stripe.Product, "create_async", new=AsyncMock(return_value=fake_product)
    ):
        result = await _provider().create_product("My Plan", "A description")

    assert isinstance(result, ExternalProduct)
    assert result.external_id == "prod_new"


@pytest.mark.asyncio
async def test_create_product_stripe_error_raises():
    with patch.object(
        stripe.Product,
        "create_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().create_product("X", None)


@pytest.mark.asyncio
async def test_create_product_no_description():
    fake_product = MagicMock()
    fake_product.id = "prod_no_desc"

    with patch.object(
        stripe.Product, "create_async", new=AsyncMock(return_value=fake_product)
    ):
        result = await _provider().create_product("No Desc Plan", None)

    assert result.external_id == "prod_no_desc"


# ---------------------------------------------------------------------------
# update_product
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_product_success():
    fake_product = MagicMock()
    fake_product.id = "prod_upd"

    with patch.object(
        stripe.Product, "modify_async", new=AsyncMock(return_value=fake_product)
    ):
        result = await _provider().update_product("prod_upd", "New Name", "New desc")

    assert result.external_id == "prod_upd"


@pytest.mark.asyncio
async def test_update_product_stripe_error_raises():
    with patch.object(
        stripe.Product,
        "modify_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().update_product("prod_x", "N", None)


# ---------------------------------------------------------------------------
# archive_product
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archive_product_success():
    with patch.object(
        stripe.Product, "modify_async", new=AsyncMock(return_value=MagicMock())
    ):
        await _provider().archive_product("prod_arc")  # should not raise


@pytest.mark.asyncio
async def test_archive_product_stripe_error_raises():
    with patch.object(
        stripe.Product,
        "modify_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().archive_product("prod_arc")


# ---------------------------------------------------------------------------
# create_price
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_price_success():
    fake_price = MagicMock()
    fake_price.id = "price_new"

    with patch.object(
        stripe.Price, "create_async", new=AsyncMock(return_value=fake_price)
    ):
        result = await _provider().create_price("prod_123", 999, "usd", "month", 1)

    assert isinstance(result, ExternalPrice)
    assert result.external_id == "price_new"


@pytest.mark.asyncio
async def test_create_price_stripe_error_raises():
    with patch.object(
        stripe.Price,
        "create_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().create_price("prod_x", 100, "usd", "month", 1)


# ---------------------------------------------------------------------------
# archive_price
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archive_price_success():
    with patch.object(
        stripe.Price, "modify_async", new=AsyncMock(return_value=MagicMock())
    ):
        await _provider().archive_price("price_arc")


@pytest.mark.asyncio
async def test_archive_price_stripe_error_raises():
    with patch.object(
        stripe.Price,
        "modify_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().archive_price("price_arc")


# ---------------------------------------------------------------------------
# get_or_create_customer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_customer_existing():
    existing_cus = MagicMock()
    existing_cus.id = "cus_existing"
    search_result = MagicMock()
    search_result.data = [existing_cus]

    with patch.object(
        stripe.Customer, "search_async", new=AsyncMock(return_value=search_result)
    ):
        result = await _provider().get_or_create_customer(
            1, "Acme Corp", email="owner@acme.com"
        )

    assert result == "cus_existing"


@pytest.mark.asyncio
async def test_get_or_create_customer_creates_new():
    search_result = MagicMock()
    search_result.data = []
    new_cus = MagicMock()
    new_cus.id = "cus_brand_new"

    with (
        patch.object(
            stripe.Customer, "search_async", new=AsyncMock(return_value=search_result)
        ),
        patch.object(
            stripe.Customer, "create_async", new=AsyncMock(return_value=new_cus)
        ),
    ):
        result = await _provider().get_or_create_customer(2, "Globex", email=None)

    assert result == "cus_brand_new"


@pytest.mark.asyncio
async def test_get_or_create_customer_creates_new_with_email():
    """Covers the `if email: params['email'] = email` branch (line 156)."""
    search_result = MagicMock()
    search_result.data = []
    new_cus = MagicMock()
    new_cus.id = "cus_with_email"

    with (
        patch.object(
            stripe.Customer, "search_async", new=AsyncMock(return_value=search_result)
        ),
        patch.object(
            stripe.Customer, "create_async", new=AsyncMock(return_value=new_cus)
        ) as mock_create,
    ):
        result = await _provider().get_or_create_customer(
            4, "Acme", email="owner@acme.com"
        )

    assert result == "cus_with_email"
    call_kwargs = mock_create.call_args[1]
    assert call_kwargs.get("email") == "owner@acme.com"


@pytest.mark.asyncio
async def test_get_or_create_customer_stripe_error_raises():
    with patch.object(
        stripe.Customer,
        "search_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().get_or_create_customer(3, "X Corp")


# ---------------------------------------------------------------------------
# update_customer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_customer_success():
    with patch.object(
        stripe.Customer, "modify_async", new=AsyncMock(return_value=MagicMock())
    ):
        await _provider().update_customer("cus_123", "new@email.com")


@pytest.mark.asyncio
async def test_update_customer_stripe_error_raises():
    with patch.object(
        stripe.Customer,
        "modify_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().update_customer("cus_x", "x@y.com")


# ---------------------------------------------------------------------------
# create_checkout_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_checkout_session_success():
    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/session123"
    fake_session.id = "cs_test123"

    with patch.object(
        stripe.checkout.Session,
        "create_async",
        new=AsyncMock(return_value=fake_session),
    ):
        result = await _provider().create_checkout_session(
            external_customer_id="cus_123",
            external_price_id="price_123",
            amount=999,
            success_url="https://app.com/success",
            cancel_url="https://app.com/cancel",
            metadata={"org_id": "1"},
            trial_period_days=None,
        )

    assert isinstance(result, CheckoutResult)
    assert result.checkout_url == "https://checkout.stripe.com/session123"
    assert result.external_session_id == "cs_test123"


@pytest.mark.asyncio
async def test_create_checkout_session_with_trial():
    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/trial_session"
    fake_session.id = "cs_trial"

    with patch.object(
        stripe.checkout.Session,
        "create_async",
        new=AsyncMock(return_value=fake_session),
    ):
        result = await _provider().create_checkout_session(
            external_customer_id=None,
            external_price_id="price_123",
            amount=999,
            success_url="https://app.com/success",
            cancel_url="https://app.com/cancel",
            metadata={},
            trial_period_days=14,
        )

    assert result.external_session_id == "cs_trial"


@pytest.mark.asyncio
async def test_create_checkout_session_free_plan():
    """Free plan (amount=0) should set payment_method_collection=if_required."""
    fake_session = MagicMock()
    fake_session.url = "https://checkout.stripe.com/free"
    fake_session.id = "cs_free"

    with patch.object(
        stripe.checkout.Session,
        "create_async",
        new=AsyncMock(return_value=fake_session),
    ) as mock_create:
        await _provider().create_checkout_session(
            external_customer_id="cus_123",
            external_price_id="price_free",
            amount=0,
            success_url="https://app.com/success",
            cancel_url="https://app.com/cancel",
            metadata={},
        )
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs.get("payment_method_collection") == "if_required"


@pytest.mark.asyncio
async def test_create_checkout_session_stripe_error_raises():
    with patch.object(
        stripe.checkout.Session,
        "create_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().create_checkout_session(
                external_customer_id=None,
                external_price_id="price_x",
                amount=100,
                success_url="https://x.com",
                cancel_url="https://x.com",
                metadata={},
            )


# ---------------------------------------------------------------------------
# cancel_subscription
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_subscription_success():
    fake_sub = _fake_sub(cancel_at_period_end=True)

    with patch.object(
        stripe.Subscription, "modify_async", new=AsyncMock(return_value=fake_sub)
    ):
        result = await _provider().cancel_subscription("sub_123")

    assert isinstance(result, ExternalSubscription)
    assert result.cancel_at_period_end is True


@pytest.mark.asyncio
async def test_cancel_subscription_stripe_error_raises():
    with patch.object(
        stripe.Subscription,
        "modify_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().cancel_subscription("sub_x")


# ---------------------------------------------------------------------------
# delete_subscription
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_subscription_success():
    with patch.object(
        stripe.Subscription, "cancel_async", new=AsyncMock(return_value=MagicMock())
    ):
        await _provider().delete_subscription("sub_123")


@pytest.mark.asyncio
async def test_delete_subscription_stripe_error_raises():
    with patch.object(
        stripe.Subscription,
        "cancel_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().delete_subscription("sub_x")


# ---------------------------------------------------------------------------
# resume_subscription
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_subscription_active():
    """Non-paused subscription > modify (remove cancel_at_period_end)."""
    current = _fake_sub(status="active", cancel_at_period_end=True)
    resumed = _fake_sub(cancel_at_period_end=False)

    with (
        patch.object(
            stripe.Subscription, "retrieve_async", new=AsyncMock(return_value=current)
        ),
        patch.object(
            stripe.Subscription, "modify_async", new=AsyncMock(return_value=resumed)
        ),
    ):
        result = await _provider().resume_subscription("sub_123")

    assert result.cancel_at_period_end is False


@pytest.mark.asyncio
async def test_resume_subscription_paused():
    """Paused subscription > resume via Subscription.resume_async."""
    current = _fake_sub(status="paused")
    resumed = _fake_sub(status="active")

    with (
        patch.object(
            stripe.Subscription, "retrieve_async", new=AsyncMock(return_value=current)
        ),
        patch.object(
            stripe.Subscription, "resume_async", new=AsyncMock(return_value=resumed)
        ),
    ):
        result = await _provider().resume_subscription("sub_123")

    assert result.status == "active"


@pytest.mark.asyncio
async def test_resume_subscription_stripe_error_raises():
    with patch.object(
        stripe.Subscription,
        "retrieve_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().resume_subscription("sub_x")


# ---------------------------------------------------------------------------
# switch_subscription_price
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_switch_subscription_price_success():
    item = MagicMock()
    item.id = "si_123"
    item.price.id = "price_old"
    item.current_period_start = 1700000000
    item.current_period_end = 1702000000

    current = _fake_sub()
    current.items.data = [item]

    updated = _fake_sub(price_id="price_new")

    with (
        patch.object(
            stripe.Subscription, "retrieve_async", new=AsyncMock(return_value=current)
        ),
        patch.object(
            stripe.Subscription, "modify_async", new=AsyncMock(return_value=updated)
        ),
    ):
        result = await _provider().switch_subscription_price("sub_123", "price_new")

    assert result.external_price_id == "price_new"


@pytest.mark.asyncio
async def test_switch_subscription_price_no_items_raises():
    current = _fake_sub()
    current.items.data = []

    with patch.object(
        stripe.Subscription, "retrieve_async", new=AsyncMock(return_value=current)
    ):
        with pytest.raises(BillingProviderException, match="no items"):
            await _provider().switch_subscription_price("sub_123", "price_new")


@pytest.mark.asyncio
async def test_switch_subscription_price_stripe_error_raises():
    with patch.object(
        stripe.Subscription,
        "retrieve_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().switch_subscription_price("sub_x", "price_y")


# ---------------------------------------------------------------------------
# create_subscription
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_subscription_success():
    fake_sub = _fake_sub(status="active")

    with patch.object(
        stripe.Subscription, "create_async", new=AsyncMock(return_value=fake_sub)
    ):
        result = await _provider().create_subscription("cus_123", "price_123")

    assert isinstance(result, ExternalSubscription)
    assert result.status == "active"


@pytest.mark.asyncio
async def test_create_subscription_with_trial():
    fake_sub = _fake_sub(status="trialing")

    with patch.object(
        stripe.Subscription, "create_async", new=AsyncMock(return_value=fake_sub)
    ):
        result = await _provider().create_subscription(
            "cus_123", "price_123", trial_period_days=14
        )

    assert result.status == "trialing"


@pytest.mark.asyncio
async def test_create_subscription_stripe_error_raises():
    with patch.object(
        stripe.Subscription,
        "create_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().create_subscription("cus_x", "price_y")


# ---------------------------------------------------------------------------
# has_payment_method
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_has_payment_method_true():
    pm = MagicMock()
    pm_list = MagicMock()
    pm_list.data = [pm]

    with patch.object(
        stripe.PaymentMethod, "list_async", new=AsyncMock(return_value=pm_list)
    ):
        assert await _provider().has_payment_method("cus_123") is True


@pytest.mark.asyncio
async def test_has_payment_method_false():
    pm_list = MagicMock()
    pm_list.data = []

    with patch.object(
        stripe.PaymentMethod, "list_async", new=AsyncMock(return_value=pm_list)
    ):
        assert await _provider().has_payment_method("cus_123") is False


@pytest.mark.asyncio
async def test_has_payment_method_stripe_error_raises():
    with patch.object(
        stripe.PaymentMethod,
        "list_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().has_payment_method("cus_x")


# ---------------------------------------------------------------------------
# get_customer_portal_url
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_customer_portal_url_success():
    fake_session = MagicMock()
    fake_session.url = "https://billing.stripe.com/portal/test"

    with patch.object(
        stripe.billing_portal.Session,
        "create_async",
        new=AsyncMock(return_value=fake_session),
    ):
        result = await _provider().get_customer_portal_url(
            "cus_123", "https://app.com/return"
        )

    assert isinstance(result, CustomerPortalResult)
    assert "billing.stripe.com" in result.portal_url


@pytest.mark.asyncio
async def test_get_customer_portal_url_stripe_error_raises():
    with patch.object(
        stripe.billing_portal.Session,
        "create_async",
        new=AsyncMock(side_effect=stripe.StripeError("err")),
    ):
        with pytest.raises(BillingProviderException):
            await _provider().get_customer_portal_url("cus_x", "https://app.com")


# ---------------------------------------------------------------------------
# construct_webhook_event
# ---------------------------------------------------------------------------


def test_construct_webhook_event_valid():
    fake_event = MagicMock()
    fake_event.id = "evt_test123"
    fake_event.type = "customer.subscription.updated"
    fake_event.to_dict.return_value = {"id": "evt_test123"}

    with patch.object(stripe.Webhook, "construct_event", return_value=fake_event):
        result = _provider().construct_webhook_event(b"payload", "sig_header")

    assert result.external_event_id == "evt_test123"
    assert result.event_type == "customer.subscription.updated"


def test_construct_webhook_event_invalid_signature_raises():
    with patch.object(
        stripe.Webhook,
        "construct_event",
        side_effect=stripe.SignatureVerificationError("bad sig", "sig"),
    ):
        with pytest.raises(BillingWebhookException):
            _provider().construct_webhook_event(b"payload", "bad_sig")


def test_construct_webhook_event_stripe_error_raises():
    with patch.object(
        stripe.Webhook,
        "construct_event",
        side_effect=stripe.StripeError("parse error"),
    ):
        with pytest.raises(BillingProviderException):
            _provider().construct_webhook_event(b"payload", "sig")


def test_construct_webhook_event_unknown_type_passthrough():
    """Unknown event types are passed through without normalization."""
    fake_event = MagicMock()
    fake_event.id = "evt_unknown"
    fake_event.type = "some.unknown.event"
    fake_event.to_dict.return_value = {}

    with patch.object(stripe.Webhook, "construct_event", return_value=fake_event):
        result = _provider().construct_webhook_event(b"payload", "sig")

    assert result.event_type == "some.unknown.event"


# ---------------------------------------------------------------------------
# _map_subscription edge case - no items
# ---------------------------------------------------------------------------


def test_map_subscription_no_items():
    sub = MagicMock()
    sub.id = "sub_empty"
    sub.customer = "cus_empty"
    sub.status = "active"
    sub.cancel_at_period_end = False
    sub.canceled_at = None
    sub.cancel_at = None
    sub.trial_end = None
    sub.items.data = []

    result = StripeProvider._map_subscription(sub)
    assert result.external_price_id is None
    assert result.current_period_start is None


def test_map_subscription_with_canceled_at():
    sub = _fake_sub(canceled_at=1700000000)
    result = StripeProvider._map_subscription(sub)
    assert result.canceled_at is not None
