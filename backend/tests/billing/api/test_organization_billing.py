"""Organizations and billing: a new organization's free subscription, and no
Stripe sync on renames."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.billing.utils import get_billing_account
from tests.conftest import TestSessionLocal


async def _seed_external_customer(
    organization_id: int,
    external_customer_id: str,
) -> None:
    async with TestSessionLocal() as session:
        account = await get_billing_account(session, organization_id)
        account.external_customer_id = external_customer_id
        await session.commit()


def test_create_an_organization_creates_free_subscription(
    admin_authenticated: TestClient,
    mock_billing_provider: MagicMock,
) -> None:
    admin_authenticated.post("/v1/organizations", json={"name": "billed organization"})

    # No Stripe customer is created at registration - deferred to trial or checkout
    mock_billing_provider.get_or_create_customer.assert_not_called()
    # Free plan subscription is local-only - no provider subscription is created
    mock_billing_provider.create_subscription.assert_not_called()


async def test_patch_organization_name_does_not_sync_to_stripe(
    admin_authenticated: TestClient,
    mock_billing_provider: MagicMock,
) -> None:
    # Org name is an app-only concept; the Stripe customer name is owned by
    # Stripe (set at checkout / editable via the customer portal) and must not
    # be overwritten when the organization is renamed.
    await _seed_external_customer(organization_id=1, external_customer_id="cus_test123")

    response = admin_authenticated.patch(
        "/v1/organizations/1",
        json={"name": "Renamed Org"},
    )

    assert response.status_code == 200
    mock_billing_provider.update_customer.assert_not_called()
