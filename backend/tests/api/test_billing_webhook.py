from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy import delete, select

from src.platform.billing.types import WebhookPayload
from src.platform.core.exceptions import (
    BillingProviderException,
    BillingWebhookException,
)
from src.platform.models.billing import PlanPrice, Subscription
from src.platform.models.organization import Organization
from tests.conftest import TestSessionLocal


def test_webhook_valid_payload(
    client: TestClient, mock_billing_provider: MagicMock
) -> None:
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_001",
        event_type="customer.subscription.updated",
        raw={"data": {"object": {"id": "sub_unknown", "status": "active"}}},
    )
    response = client.post(
        "/v1/billing/webhook",
        content=b"test_payload",
        headers={"stripe-signature": "sig_test"},
    )
    assert response.status_code == 200
    assert response.json() == {"received": True}


def test_webhook_invalid_signature(
    client: TestClient, mock_billing_provider: MagicMock
) -> None:
    mock_billing_provider.construct_webhook_event.side_effect = BillingWebhookException(
        "Invalid webhook signature"
    )
    response = client.post(
        "/v1/billing/webhook",
        content=b"bad_payload",
        headers={"stripe-signature": "bad_sig"},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "billing_webhook_invalid"


def test_webhook_idempotency(
    client: TestClient, mock_billing_provider: MagicMock
) -> None:
    payload = WebhookPayload(
        external_event_id="evt_idempotent_001",
        event_type="customer.subscription.updated",
        raw={"data": {"object": {"id": "sub_noop", "status": "active"}}},
    )

    # Send twice
    for _ in range(2):
        mock_billing_provider.construct_webhook_event.return_value = payload
        resp = client.post(
            "/v1/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "sig"},
        )
        assert resp.status_code == 200

    # The event should be recorded once - second call is a no-op after "processed"
    assert mock_billing_provider.construct_webhook_event.call_count == 2


def test_webhook_checkout_completed_updates_subscription(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    price_id = plan_with_price["price"]["id"]

    # Initiate checkout - subscription row is NOT changed (stays as active free)
    admin_authenticated.post(
        "/v1/billing/subscriptions/checkout",
        json={"plan_price_id": price_id},
    )

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"
    assert sub["plan_price"]["amount"] == 0  # still on free plan

    # Fire checkout.session.completed webhook
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_checkout_done",
        event_type="checkout.session.completed",
        raw={
            "data": {
                "object": {
                    "subscription": "sub_activated_123",
                    "customer": "cus_test123",
                    "metadata": {"plan_price_id": str(price_id)},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig"},
    )
    assert resp.status_code == 200

    # external_subscription_id is stamped by checkout.session.completed; status
    # is set by the subsequent customer.subscription.created event from Stripe.
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_created",
        event_type="customer.subscription.created",
        raw={
            "data": {
                "object": {
                    "id": "sub_activated_123",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "canceled_at": None,
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    admin_authenticated.post(
        "/v1/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "sig2"},
    )

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"


def test_webhook_subscription_deleted(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    price_id = plan_with_price["price"]["id"]

    # Set up an active subscription
    admin_authenticated.post(
        "/v1/billing/subscriptions/checkout",
        json={"plan_price_id": price_id},
    )
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_activate_for_delete",
        event_type="checkout.session.completed",
        raw={
            "data": {
                "object": {
                    "subscription": "sub_to_delete",
                    "customer": "cus_test123",
                    "metadata": {"plan_price_id": str(price_id)},
                }
            }
        },
    )
    admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )

    # Fire subscription.deleted
    canceled_ts = int(datetime.now(UTC).timestamp())
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_deleted",
        event_type="customer.subscription.deleted",
        raw={
            "data": {
                "object": {
                    "id": "sub_to_delete",
                    "canceled_at": canceled_ts,
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    # Subscription is restored to the free plan; org is never left without one.
    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"
    assert sub["plan_price"]["amount"] == 0


def test_webhook_payment_failed_does_not_downgrade(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    """
    First payment failure must not downgrade - Stripe Smart Retries are still
    pending. Status moves to past_due (which retains access) but the plan
    stays untouched.
    """
    price_id = plan_with_price["price"]["id"]

    # Set up an active subscription
    admin_authenticated.post(
        "/v1/billing/subscriptions/checkout", json={"plan_price_id": price_id}
    )
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_activate_for_fail",
        event_type="checkout.session.completed",
        raw={
            "data": {
                "object": {
                    "subscription": "sub_payment_fail",
                    "customer": "cus_test123",
                    "metadata": {"plan_price_id": str(price_id)},
                }
            }
        },
    )
    admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )

    # Stripe fires subscription.created right after checkout - sets status to active
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_created_for_fail",
        event_type="customer.subscription.created",
        raw={
            "data": {
                "object": {
                    "id": "sub_payment_fail",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "canceled_at": None,
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s2"}
    )

    # Fire invoice.payment_failed - plan must NOT be touched
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_payment_failed",
        event_type="invoice.payment_failed",
        raw={
            "data": {
                "object": {
                    "subscription": "sub_payment_fail",
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "past_due"
    # Plan price must remain unchanged - no downgrade on first failure
    assert sub["plan_price"]["id"] == price_id
    mock_billing_provider.switch_subscription_price.assert_not_called()


def test_webhook_subscription_updated(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    price_id = plan_with_price["price"]["id"]

    admin_authenticated.post(
        "/v1/billing/subscriptions/checkout",
        json={"plan_price_id": price_id},
    )
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_activate_for_update",
        event_type="checkout.session.completed",
        raw={
            "data": {
                "object": {
                    "subscription": "sub_to_update",
                    "customer": "cus_test123",
                    "metadata": {"plan_price_id": str(price_id)},
                }
            }
        },
    )
    admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )

    now_ts = int(datetime.now(UTC).timestamp())
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_updated",
        event_type="customer.subscription.updated",
        raw={
            "data": {
                "object": {
                    "id": "sub_to_update",
                    "status": "past_due",
                    "cancel_at_period_end": True,
                    "current_period_start": now_ts,
                    "current_period_end": now_ts + 2592000,
                    "canceled_at": None,
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "past_due"
    assert sub["cancel_at_period_end"] is True


def _activate_sub(
    client: TestClient,
    price_id: int,
    mock_billing_provider: MagicMock,
    event_id: str,
    sub_id: str,
) -> None:
    client.post("/v1/billing/subscriptions/checkout", json={"plan_price_id": price_id})
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id=event_id,
        event_type="checkout.session.completed",
        raw={
            "data": {
                "object": {
                    "subscription": sub_id,
                    "customer": "cus_test123",
                    "metadata": {"plan_price_id": str(price_id)},
                }
            }
        },
    )
    client.post("/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"})


def test_webhook_subscription_created(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    price_id = plan_with_price["price"]["id"]
    admin_authenticated.post(
        "/v1/billing/subscriptions/checkout", json={"plan_price_id": price_id}
    )

    # subscription.created fires before checkout.session.completed in Stripe's order;
    # external_subscription_id not yet set - handler must fall back to customer lookup.
    now_ts = int(datetime.now(UTC).timestamp())
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_created",
        event_type="customer.subscription.created",
        raw={
            "data": {
                "object": {
                    "id": "sub_created_123",
                    "customer": "cus_test123",
                    "status": "trialing",
                    "cancel_at_period_end": False,
                    "current_period_start": now_ts,
                    "current_period_end": now_ts + 1209600,
                    "canceled_at": None,
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "trialing"
    assert sub["current_period_start"] is not None
    assert sub["current_period_end"] is not None


def test_webhook_checkout_session_expired(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    """
    checkout.session.expired is a no-op for free-plan users: the subscription
    stays "active" because start_checkout no longer creates an incomplete row.
    The handler only acts on genuinely incomplete rows (status="incomplete").
    """
    price_id = plan_with_price["price"]["id"]

    # Checkout does not change the free subscription row
    admin_authenticated.post(
        "/v1/billing/subscriptions/checkout", json={"plan_price_id": price_id}
    )
    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"
    assert sub["plan_price"]["amount"] == 0

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_checkout_expired",
        event_type="checkout.session.expired",
        raw={
            "data": {
                "object": {
                    "customer": "cus_test123",
                    "metadata": {"plan_price_id": str(price_id)},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    # Free subscription unchanged - session expiry is a no-op here
    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"
    assert sub["plan_price"]["amount"] == 0


def test_webhook_payment_action_required_sets_incomplete(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    price_id = plan_with_price["price"]["id"]
    _activate_sub(
        admin_authenticated, price_id, mock_billing_provider, "evt_act_pam", "sub_pam"
    )

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_payment_action_required",
        event_type="invoice.payment_action_required",
        raw={"data": {"object": {"subscription": "sub_pam"}}},
    )
    admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )

    # Stripe fires customer.subscription.updated alongside the invoice event
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_payment_action_required_sub_updated",
        event_type="customer.subscription.updated",
        raw={
            "data": {
                "object": {
                    "id": "sub_pam",
                    "status": "incomplete",
                    "cancel_at_period_end": False,
                    "canceled_at": None,
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200
    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "incomplete"


def test_webhook_marked_uncollectible_downgrades_to_free_plan(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    """
    All Stripe retries exhausted - subscription should be downgraded to free.
    """
    price_id = plan_with_price["price"]["id"]
    _activate_sub(
        admin_authenticated, price_id, mock_billing_provider, "evt_act_muc", "sub_muc"
    )

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_marked_uncollectible",
        event_type="invoice.marked_uncollectible",
        raw={"data": {"object": {"subscription": "sub_muc"}}},
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"
    assert sub["plan_price"]["amount"] == 0
    mock_billing_provider.delete_subscription.assert_called_once_with("sub_muc")
    mock_billing_provider.switch_subscription_price.assert_not_called()


def test_webhook_charge_dispute_marks_past_due(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    """
    A chargeback flags the subscription as past_due (access retained, banner
    shown) without touching the plan; final access removal is left to the
    dispute outcome (subscription cancellation / uncollectible flow).
    """
    price_id = plan_with_price["price"]["id"]
    _activate_sub(
        admin_authenticated, price_id, mock_billing_provider, "evt_act_disp", "sub_disp"
    )

    # subscription.created sets the status to active
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_created_for_dispute",
        event_type="customer.subscription.created",
        raw={
            "data": {
                "object": {
                    "id": "sub_disp",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "canceled_at": None,
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )

    mock_billing_provider.get_charge_customer.return_value = "cus_test123"
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_dispute_created",
        event_type="charge.dispute.created",
        raw={"data": {"object": {"charge": "ch_disputed"}}},
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    mock_billing_provider.get_charge_customer.assert_called_once_with("ch_disputed")
    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "past_due"
    assert sub["plan_price"]["id"] == price_id
    mock_billing_provider.delete_subscription.assert_not_called()


def test_webhook_subscription_updated_noop_skips_plan_changed_hook(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
    mocker,
) -> None:
    """
    subscription.updated events that change neither status nor price (e.g.
    billing-anchor or metadata updates) must not emit PLAN_CHANGED; a real
    status change must.
    """
    price_id = plan_with_price["price"]["id"]
    _activate_sub(
        admin_authenticated, price_id, mock_billing_provider, "evt_act_noop", "sub_noop"
    )
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_created_for_noop",
        event_type="customer.subscription.created",
        raw={
            "data": {
                "object": {
                    "id": "sub_noop",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "canceled_at": None,
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )

    emit_mock = mocker.patch("src.platform.services.billing.emit")

    # Same status, same price - only the billing period moved.
    now_ts = int(datetime.now(UTC).timestamp())
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_updated_noop",
        event_type="customer.subscription.updated",
        raw={
            "data": {
                "object": {
                    "id": "sub_noop",
                    "status": "active",
                    "current_period_start": now_ts,
                    "current_period_end": now_ts + 2592000,
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200
    emit_mock.assert_not_called()

    # Status change - hook must fire.
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_updated_status_change",
        event_type="customer.subscription.updated",
        raw={
            "data": {
                "object": {
                    "id": "sub_noop",
                    "status": "past_due",
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200
    emit_mock.assert_called_once()


def test_webhook_subscription_unpaid_downgrades_to_free_plan(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    """
    Stripe exhausted dunning and marked the subscription unpaid - the org is
    downgraded to free and the Stripe subscription is canceled.
    """
    price_id = plan_with_price["price"]["id"]
    _activate_sub(
        admin_authenticated, price_id, mock_billing_provider, "evt_act_unp", "sub_unp"
    )

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_unpaid",
        event_type="customer.subscription.updated",
        raw={
            "data": {
                "object": {
                    "id": "sub_unp",
                    "status": "unpaid",
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"
    assert sub["plan_price"]["amount"] == 0
    mock_billing_provider.delete_subscription.assert_called_once_with("sub_unp")


def test_webhook_subscription_incomplete_expired_downgrades_to_free_plan(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    """
    The initial payment never completed and the subscription expired. The org
    is reset to free; no Stripe cancellation is attempted because the
    subscription is already terminal on Stripe's side.
    """
    price_id = plan_with_price["price"]["id"]
    _activate_sub(
        admin_authenticated, price_id, mock_billing_provider, "evt_act_exp", "sub_exp"
    )

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_incomplete_expired",
        event_type="customer.subscription.updated",
        raw={
            "data": {
                "object": {
                    "id": "sub_exp",
                    "status": "incomplete_expired",
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"
    assert sub["plan_price"]["amount"] == 0
    mock_billing_provider.delete_subscription.assert_not_called()


def test_webhook_product_created(
    admin_authenticated: TestClient,
    mock_billing_provider: MagicMock,
) -> None:
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_product_created",
        event_type="product.created",
        raw={
            "data": {
                "object": {
                    "id": "prod_stripe_new",
                    "name": "Stripe Plan",
                    "description": "Created in Stripe",
                    "active": True,
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    plans = admin_authenticated.get("/v1/billing/plans").json()
    created = next((p for p in plans if p["name"] == "Stripe Plan"), None)
    assert created is not None
    assert created["description"] == "Created in Stripe"


def test_webhook_product_created_already_exists(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    # plan_with_price already has external_product_id="prod_test123"
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_product_created_dup",
        event_type="product.created",
        raw={
            "data": {
                "object": {
                    "id": "prod_test123",
                    "name": "Duplicate",
                    "description": None,
                    "active": True,
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    plans = admin_authenticated.get("/v1/billing/plans").json()
    matching = [p for p in plans if p["name"] == "Duplicate"]
    assert len(matching) == 0  # no duplicate created


def test_webhook_product_updated(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_product_updated",
        event_type="product.updated",
        raw={
            "data": {
                "object": {
                    "id": "prod_test123",
                    "name": "Updated Name",
                    "description": "Updated desc",
                    "active": False,
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    plans = admin_authenticated.get("/v1/billing/plans").json()
    # is_active=False means it won't appear in list_plans (which filters active only)
    assert not any(p["name"] == "Updated Name" for p in plans)


def test_webhook_price_created(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    plan_id = plan_with_price["plan"]["id"]

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_price_created",
        event_type="price.created",
        raw={
            "data": {
                "object": {
                    "id": "price_stripe_new",
                    "product": "prod_test123",
                    "unit_amount": 4999,
                    "currency": "dkk",
                    "active": True,
                    "recurring": {"interval": "year", "interval_count": 1},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    plan = admin_authenticated.get(f"/v1/billing/plans/{plan_id}").json()
    new_price = next(
        (p for p in plan["prices"] if p["amount"] == 4999 and p["interval"] == "year"),
        None,
    )
    assert new_price is not None


def test_webhook_price_created_unknown_product(
    admin_authenticated: TestClient,
    mock_billing_provider: MagicMock,
) -> None:
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_price_created_unknown",
        event_type="price.created",
        raw={
            "data": {
                "object": {
                    "id": "price_orphan",
                    "product": "prod_nonexistent",
                    "unit_amount": 999,
                    "currency": "dkk",
                    "active": True,
                    "recurring": {"interval": "month", "interval_count": 1},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200  # no crash


@pytest.fixture
async def free_plan_subscription(plan_with_price: dict) -> dict:
    """
    Set up organization 1 with an active free-plan subscription and Stripe customer ID.
    Simulates a user assigned the free plan by _setup_new_organization.
    """
    async with TestSessionLocal() as session:
        organization = await session.get(Organization, 1)
        assert organization is not None
        organization.external_customer_id = "cus_free123"
        free_price = (
            await session.execute(select(PlanPrice).where(PlanPrice.amount == 0))
        ).scalar_one()
        free_price_id = free_price.id  # capture before session closes
        # Update the existing free subscription rather than inserting a new row
        sub = (
            await session.execute(
                select(Subscription).where(Subscription.organization_id == 1)
            )
        ).scalar_one()
        sub.plan_price_id = free_price_id
        sub.status = "active"
        sub.external_subscription_id = None
        await session.commit()
    return {"free_price_id": free_price_id}


async def test_free_plan_user_checkout_upgrades_to_trial(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    free_plan_subscription: dict,
    mock_billing_provider: MagicMock,
) -> None:
    """
    A user registered on the free plan completes a Stripe checkout session.
    The subscription should be updated to the paid plan with trial status.
    This covers both event orderings (subscription.created before/after
    checkout.session.completed).
    """
    price_id = plan_with_price["price"]["id"]

    # Verify starting state: active free plan, no Stripe subscription
    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"
    assert sub["plan_price"]["amount"] == 0

    # Start checkout - should succeed for active free-plan users
    resp = admin_authenticated.post(
        "/v1/billing/subscriptions/checkout",
        json={"plan_price_id": price_id},
    )
    assert resp.status_code == 200

    # Simulate: customer.subscription.created fires BEFORE checkout.session.completed
    # (race condition - _handle_subscription_created falls back to customer lookup)
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_created_free",
        event_type="customer.subscription.created",
        raw={
            "data": {
                "object": {
                    "id": "sub_from_free123",
                    "customer": "cus_free123",
                    "status": "trialing",
                    "cancel_at_period_end": False,
                    "canceled_at": None,
                    "trial_end": int(datetime(2026, 5, 15, tzinfo=UTC).timestamp()),
                    "items": {"data": [{"price": {"id": "price_test123"}}]},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s1"}
    )
    assert resp.status_code == 200

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "trialing"
    assert sub["plan_price"]["amount"] == 999  # paid plan
    assert sub["trial_end"] is not None


@pytest.fixture
async def trialing_subscription(plan_with_price: dict) -> dict:
    """Set the existing subscription for organization 1 to trialing state."""
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        organization = await session.get(Organization, 1)
        if organization and not organization.external_customer_id:
            organization.external_customer_id = "cus_test123"
        sub = (
            await session.execute(
                select(Subscription).where(Subscription.organization_id == 1)
            )
        ).scalar_one()
        sub.plan_price_id = price_id
        sub.external_subscription_id = "sub_trial"
        sub.status = "trialing"
        await session.commit()
    return {"external_subscription_id": "sub_trial"}


def test_webhook_subscription_trial_will_end_sends_email(
    admin_authenticated: TestClient,
    trialing_subscription: dict,
    mock_billing_provider: MagicMock,
    mocker: MockerFixture,
) -> None:
    trial_end_ts = int(datetime(2026, 5, 1, tzinfo=UTC).timestamp())
    mock_send = mocker.patch("src.platform.services.billing.send_email")

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_trial_will_end",
        event_type="customer.subscription.trial_will_end",
        raw={
            "data": {
                "object": {
                    "id": "sub_trial",
                    "trial_end": trial_end_ts,
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200
    assert mock_send.called
    addresses = {call.kwargs["address"] for call in mock_send.call_args_list}
    assert "admin@example.org" in addresses
    for call in mock_send.call_args_list:
        assert call.kwargs["email_template"] == "trial-ending"
        # Recipients default to the "da" locale, so the date is rendered in Danish.
        assert call.kwargs["data"]["trial_end_date"] == "1. maj 2026"


def test_webhook_subscription_trial_will_end_unknown_sub(
    client: TestClient,
    mock_billing_provider: MagicMock,
) -> None:
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_trial_unknown",
        event_type="customer.subscription.trial_will_end",
        raw={"data": {"object": {"id": "sub_nonexistent", "trial_end": None}}},
    )
    resp = client.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200  # silently ignored


def test_webhook_price_updated(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    mock_billing_provider: MagicMock,
) -> None:
    plan_id = plan_with_price["plan"]["id"]

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_price_updated",
        event_type="price.updated",
        raw={
            "data": {
                "object": {
                    "id": "price_test123",
                    "active": False,
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    plan = admin_authenticated.get(f"/v1/billing/plans/{plan_id}").json()
    price = next(p for p in plan["prices"] if p["id"] == plan_with_price["price"]["id"])
    assert price["is_active"] is False


def test_webhook_uncollectible_downgrades_to_free_plan(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    trialing_subscription: dict,
    mock_billing_provider: MagicMock,
) -> None:
    """
    invoice.marked_uncollectible (all retries exhausted) should downgrade to free.
    """
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_uncollectible_downgrade",
        event_type="invoice.marked_uncollectible",
        raw={"data": {"object": {"subscription": "sub_trial"}}},
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"
    assert sub["plan_price"]["amount"] == 0
    mock_billing_provider.delete_subscription.assert_called_once_with("sub_trial")
    mock_billing_provider.switch_subscription_price.assert_not_called()


def test_webhook_uncollectible_falls_back_gracefully_on_provider_error(
    admin_authenticated: TestClient,
    plan_with_price: dict,
    trialing_subscription: dict,
    mock_billing_provider: MagicMock,
) -> None:
    """
    When the Stripe cancellation call fails during downgrade, the webhook returns
    500 so Stripe retries. Local state is NOT changed - external_subscription_id
    remains intact so the next retry can attempt the Stripe call again.
    This prevents a lingering active Stripe subscription from generating charges.
    """
    mock_billing_provider.delete_subscription.side_effect = BillingProviderException(
        "Stripe error"
    )
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_uncollectible_fallback",
        event_type="invoice.marked_uncollectible",
        raw={"data": {"object": {"subscription": "sub_trial"}}},
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 400

    # Local state must be unchanged - subscription still on the paid plan
    # with external_subscription_id intact for retry
    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "trialing"
    assert sub["plan_price"]["amount"] == 999


@pytest.fixture
async def no_free_price() -> None:
    async with TestSessionLocal() as session:
        await session.execute(delete(PlanPrice).where(PlanPrice.amount == 0))
        await session.commit()


def test_webhook_subscription_paused_trial_end_downgrades_to_free(
    admin_authenticated: TestClient,
    trialing_subscription: dict,
    mock_billing_provider: MagicMock,
    mocker: MockerFixture,
) -> None:
    """
    Trial ended without a payment method (pause_collection is null) - subscription
    should be immediately downgraded to the free plan locally and the Stripe
    subscription cancelled.
    """
    mock_send = mocker.patch("src.platform.services.billing.send_email")

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_paused_trial_end",
        event_type="customer.subscription.paused",
        raw={
            "data": {
                "object": {
                    "id": "sub_trial",
                    "pause_collection": None,
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    mock_billing_provider.delete_subscription.assert_called_once_with("sub_trial")
    mock_billing_provider.switch_subscription_price.assert_not_called()
    mock_billing_provider.resume_subscription.assert_not_called()
    assert mock_send.called
    for call in mock_send.call_args_list:
        assert call.kwargs["email_template"] == "trial-ended"

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "active"
    assert sub["plan_price"]["amount"] == 0


def test_webhook_subscription_paused_manual_stays_paused(
    admin_authenticated: TestClient,
    trialing_subscription: dict,
    mock_billing_provider: MagicMock,
) -> None:
    """
    Explicit manual pause (pause_collection is set) - subscription should be
    marked paused and the plan price must remain unchanged.
    """
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_paused_manual",
        event_type="customer.subscription.paused",
        raw={
            "data": {
                "object": {
                    "id": "sub_trial",
                    "pause_collection": {"behavior": "void"},
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    sub = admin_authenticated.get("/v1/billing/subscriptions/current").json()
    assert sub["status"] == "paused"
    mock_billing_provider.switch_subscription_price.assert_not_called()


def test_webhook_subscription_paused_trial_end_no_free_plan_cancels(
    admin_authenticated: TestClient,
    trialing_subscription: dict,
    no_free_price: None,
    mock_billing_provider: MagicMock,
) -> None:
    """
    Trial ended without a payment method and no free plan is configured - subscription
    should be canceled rather than left in a paused limbo.
    """
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_sub_paused_no_free",
        event_type="customer.subscription.paused",
        raw={
            "data": {
                "object": {
                    "id": "sub_trial",
                    "pause_collection": None,
                }
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200

    sub_resp = admin_authenticated.get("/v1/billing/subscriptions/current")
    assert sub_resp.status_code == 404
    mock_billing_provider.delete_subscription.assert_called_once_with("sub_trial")
    mock_billing_provider.switch_subscription_price.assert_not_called()


def test_webhook_payment_method_attached_sets_flag(
    admin_authenticated: TestClient,
    trialing_subscription: dict,
    mock_billing_provider: MagicMock,
) -> None:
    assert (
        admin_authenticated.get("/v1/billing/subscriptions/current").json()[
            "has_payment_method"
        ]
        is False
    )

    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_pm_attached",
        event_type="payment_method.attached",
        raw={"data": {"object": {"customer": "cus_test123"}}},
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200
    assert (
        admin_authenticated.get("/v1/billing/subscriptions/current").json()[
            "has_payment_method"
        ]
        is True
    )


def test_webhook_payment_method_detached_clears_flag(
    admin_authenticated: TestClient,
    trialing_subscription: dict,
    mock_billing_provider: MagicMock,
) -> None:
    # First attach a payment method
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_pm_attached2",
        event_type="payment_method.attached",
        raw={"data": {"object": {"customer": "cus_test123"}}},
    )
    admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert (
        admin_authenticated.get("/v1/billing/subscriptions/current").json()[
            "has_payment_method"
        ]
        is True
    )

    # Now detach it - mock says no remaining methods
    mock_billing_provider.has_payment_method.return_value = False
    mock_billing_provider.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_pm_detached",
        event_type="payment_method.detached",
        raw={
            "data": {
                "object": {"customer": None},
                "previous_attributes": {"customer": "cus_test123"},
            }
        },
    )
    resp = admin_authenticated.post(
        "/v1/billing/webhook", content=b"{}", headers={"stripe-signature": "s"}
    )
    assert resp.status_code == 200
    assert (
        admin_authenticated.get("/v1/billing/subscriptions/current").json()[
            "has_payment_method"
        ]
        is False
    )
    mock_billing_provider.has_payment_method.assert_called_once_with("cus_test123")
