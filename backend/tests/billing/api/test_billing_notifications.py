from fastapi.testclient import TestClient

from src.billing.repositories.manager import BillingRepositoryManager
from src.billing.services import WebhookService
from tests.conftest import TestSessionLocal


async def test_a_billing_event_reaches_the_managers_notification_list(
    admin_authenticated: TestClient, mock_billing_provider
) -> None:
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        sub = await repos.subscription.get_active_for_organization(1)
        assert sub
        await repos.subscription.update(sub, external_subscription_id="sub_paid")
    async with TestSessionLocal() as session, session.begin():
        service = WebhookService(
            BillingRepositoryManager(session), mock_billing_provider
        )
        await service._dispatch(
            "invoice.payment_failed",
            {"data": {"object": {"subscription": "sub_paid"}}},
        )

    assert admin_authenticated.get("/v1/notifications/unread-count").json() == {
        "count": 1
    }
    [item] = admin_authenticated.get("/v1/notifications").json()["items"]
    assert item["type"] == "billing.payment-failed"
    assert item["read_at"] is None


async def test_another_organizations_notification_is_not_listed(
    admin_authenticated: TestClient,
) -> None:
    async with TestSessionLocal() as session, session.begin():
        # For the owner of organization 2 - not the signed-in admin's organization.
        await BillingRepositoryManager(session).notification.create(
            user_id=4, organization_id=2, type="billing.payment-failed", payload={}
        )

    assert admin_authenticated.get("/v1/notifications").json()["items"] == []
    assert admin_authenticated.get("/v1/notifications/unread-count").json() == {
        "count": 0
    }
