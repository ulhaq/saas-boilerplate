"""Ownership transfer -> the provider customer's email, via the worker's
customer sync (`sync_customer_emails`): a provider outage never fails the
transfer, and a failed push is retried."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text

from src.billing.exceptions import BillingProviderException
from src.billing.services.maintenance import (
    MAX_CUSTOMER_SYNC_ATTEMPTS,
    sync_customer_emails,
)
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
    return await sync_customer_emails(TestSessionLocal, provider)


async def _set_pending(organization_id: int, customer_id: str, email: str) -> None:
    async with TestSessionLocal() as session, session.begin():
        account = await get_billing_account(session, organization_id)
        account.external_customer_id = customer_id
        account.pending_customer_email = email


async def _make_due(organization_id: int) -> None:
    """Skip the account's backoff."""
    async with TestSessionLocal() as session, session.begin():
        account = await get_billing_account(session, organization_id)
        account.customer_sync_next_at = datetime.now(UTC) - timedelta(seconds=1)


async def _attempts(organization_id: int) -> int:
    async with TestSessionLocal() as session:
        account = await get_billing_account(session, organization_id)
        return account.customer_sync_attempts


def _transfer(client: TestClient) -> None:
    response = client.post(
        "/v1/organizations/1/transfer-ownership",
        json={"user_id": 2},
    )
    assert response.status_code == 204


async def test_a_transfer_queues_the_new_owner_email_and_the_sync_pushes_it(
    admin_authenticated: TestClient,
    mock_billing_provider,
):
    await _set_customer("cus_transfer")

    _transfer(admin_authenticated)

    mock_billing_provider.update_customer.assert_not_called()
    assert await _pending() == "standard@example.org"

    assert await _sync(mock_billing_provider) == 1
    mock_billing_provider.update_customer.assert_called_once_with(
        "cus_transfer",
        email="standard@example.org",
    )
    assert await _pending() is None
    assert await _sync(mock_billing_provider) == 0


async def test_a_provider_outage_does_not_fail_the_transfer_and_is_retried(
    admin_authenticated: TestClient,
    mock_billing_provider,
):
    await _set_customer("cus_transfer")
    mock_billing_provider.update_customer.side_effect = BillingProviderException("down")

    _transfer(admin_authenticated)
    assert await _sync(mock_billing_provider) == 0
    assert await _pending() == "standard@example.org"

    # Retried once its backoff has passed.
    mock_billing_provider.update_customer.side_effect = None
    await _make_due(1)
    assert await _sync(mock_billing_provider) == 1
    assert await _pending() is None


async def test_a_newer_email_set_during_a_push_stays_pending(
    admin_authenticated: TestClient,
    mock_billing_provider,
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
    admin_authenticated: TestClient,
    mock_billing_provider,
):
    _transfer(admin_authenticated)

    assert await _pending() is None
    assert await _sync(mock_billing_provider) == 0
    mock_billing_provider.update_customer.assert_not_called()


async def test_no_transaction_is_open_while_the_provider_is_called(
    admin_authenticated: TestClient,
    mock_billing_provider,
):
    """A slow provider must not hold a database connection in a transaction."""
    await _set_customer("cus_transfer")
    _transfer(admin_authenticated)
    open_during_call: list[int] = []

    async def count_open_transactions(*_args, **_kwargs):
        async with TestSessionLocal() as session:
            rs = await session.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity"
                    " WHERE datname = current_database()"
                    " AND state = 'idle in transaction'",
                ),
            )
            open_during_call.append(rs.scalar_one())

    mock_billing_provider.update_customer.side_effect = count_open_transactions

    assert await _sync(mock_billing_provider) == 1
    assert open_during_call == [0]


async def test_a_failing_account_does_not_hold_up_the_others(mock_billing_provider):
    await _set_pending(1, "cus_broken", "one@example.org")
    await _set_pending(2, "cus_fine", "two@example.org")

    async def fail_for_the_broken_customer(customer_id, **_kwargs):
        if customer_id == "cus_broken":
            raise BillingProviderException("No such customer")

    mock_billing_provider.update_customer.side_effect = fail_for_the_broken_customer

    assert await _sync(mock_billing_provider) == 1
    assert await _attempts(1) == 1
    assert await _attempts(2) == 0


async def test_a_failed_push_waits_for_its_backoff(mock_billing_provider):
    await _set_pending(1, "cus_one", "one@example.org")
    mock_billing_provider.update_customer.side_effect = BillingProviderException("down")
    await _sync(mock_billing_provider)

    # Not due yet: not even tried, though the provider is back.
    mock_billing_provider.update_customer.side_effect = None
    mock_billing_provider.update_customer.reset_mock()
    assert await _sync(mock_billing_provider) == 0
    mock_billing_provider.update_customer.assert_not_called()

    await _make_due(1)
    assert await _sync(mock_billing_provider) == 1


async def test_a_push_is_given_up_after_too_many_attempts(
    mock_billing_provider,
    caplog,
):
    await _set_pending(1, "cus_one", "one@example.org")
    async with TestSessionLocal() as session, session.begin():
        account = await get_billing_account(session, 1)
        account.customer_sync_attempts = MAX_CUSTOMER_SYNC_ATTEMPTS - 1
    mock_billing_provider.update_customer.side_effect = BillingProviderException(
        "No such customer",
    )

    assert await _sync(mock_billing_provider) == 0
    assert await _attempts(1) == MAX_CUSTOMER_SYNC_ATTEMPTS
    assert "gave up" in caplog.text

    # Never tried again, even once due; the email stays pending, for a person.
    await _make_due(1)
    mock_billing_provider.update_customer.reset_mock()
    assert await _sync(mock_billing_provider) == 0
    mock_billing_provider.update_customer.assert_not_called()
    assert await _pending() == "one@example.org"


async def test_a_new_email_starts_its_retries_fresh(
    admin_authenticated: TestClient,
    mock_billing_provider,
):
    await _set_customer("cus_transfer")
    async with TestSessionLocal() as session, session.begin():
        account = await get_billing_account(session, 1)
        account.customer_sync_attempts = MAX_CUSTOMER_SYNC_ATTEMPTS

    _transfer(admin_authenticated)

    assert await _attempts(1) == 0
    assert await _sync(mock_billing_provider) == 1
