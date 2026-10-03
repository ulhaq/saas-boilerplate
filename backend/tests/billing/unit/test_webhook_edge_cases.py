"""Billing webhook edge cases."""

from src.billing.repositories.manager import BillingRepositoryManager
from src.billing.services import WebhookService
from tests.conftest import TestSessionLocal


async def test_handle_payment_method_detached_no_customer_id(mock_billing_provider):
    """payment_method.detached returns early when no customer_id."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = BillingRepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)

            raw = {
                "data": {
                    "object": {"customer": None},
                    "previous_attributes": {},
                }
            }
            # Should complete without querying the database
            await service._dispatch("payment_method.detached", raw)

    # The organization repo must not have been touched
    mock_billing_provider.has_payment_method.assert_not_called()
