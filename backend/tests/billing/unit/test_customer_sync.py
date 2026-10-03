"""Ownership transfer -> the provider customer's email, via the worker's
customer sync (`sync_customer_emails`): a provider outage never fails the
transfer, and a failed push is retried."""

from fastapi.testclient import TestClient

from src.billing.repositories.manager import BillingRepositoryManager
from src.billing.services.maintenance import sync_customer_emails
from tests.billing.utils import get_billing_account
from tests.conftest import TestSessionLocal


async def _set_customer(customer_id: str | None) -> None:
    async with TestSessionLocal() as session, session.begin():
        account = await get_billing_account(session, 1)
        account.external_customer_id = customer_id


async def _pending() -> str | None:
    async with TestSessionLocal() as session:
        return (await get_billing_account(session, 1)).pending_customer_email


async def _sync(provider) -> int:
    async with TestSessionLocal() as session, session.begin():
        return await sync_customer_emails(BillingRepositoryManager(session), provider)


def _transfer(client: TestClient) -> None:
    response = client.post(
        "/v1/organizations/1/transfer-ownership", json={"user_id": 2}
    )
    assert response.status_code == 204


async def test_a_transfer_queues_the_new_owner_email_and_the_sync_pushes_it(
    admin_authenticated: TestClient, mock_billing_provider
):
    await _set_customer("cus_transfer")

    _transfer(admin_authenticated)

    mock_billing_provider.update_customer.assert_not_called()
    assert await _pending() == "standard@example.org"

    assert await _sync(mock_billing_provider) == 1
    mock_billing_provider.update_customer.assert_called_once_with(
        "cus_transfer", email="standard@example.org"
    )
    assert await _pending() is None
    assert await _sync(mock_billing_provider) == 0


async def test_a_provider_outage_does_not_fail_the_transfer_and_is_retried(
    admin_authenticated: TestClient, mock_billing_provider
):
    await _set_customer("cus_transfer")
    mock_billing_provider.update_customer.side_effect = ConnectionError("down")

    _transfer(admin_authenticated)
    assert await _sync(mock_billing_provider) == 0
    assert await _pending() == "standard@example.org"

    mock_billing_provider.update_customer.side_effect = None
    assert await _sync(mock_billing_provider) == 1
    assert await _pending() is None


async def test_a_newer_email_set_during_a_push_stays_pending(
    admin_authenticated: TestClient, mock_billing_provider
):
    await _set_customer("cus_transfer")
    _transfer(admin_authenticated)

    async def newer_change(*_args, **_kwargs):
        async with TestSessionLocal() as session, session.begin():
            account = await get_billing_account(session, 1)
            account.pending_customer_email = "newest@example.org"

    mock_billing_provider.update_customer.side_effect = newer_change

    assert await _sync(mock_billing_provider) == 0
    assert await _pending() == "newest@example.org"


async def test_no_provider_customer_means_nothing_to_sync(
    admin_authenticated: TestClient, mock_billing_provider
):
    _transfer(admin_authenticated)

    assert await _pending() is None
    assert await _sync(mock_billing_provider) == 0
    mock_billing_provider.update_customer.assert_not_called()
