"""Billing's share of a user's data export (GDPR)."""

from typing import Any

from src.billing.repositories.manager import BillingRepositoryManager
from src.platform.repositories.repository_manager import RepositoryManager


async def export_user_data(
    *, repos: RepositoryManager, user_id: int, email: str
) -> dict[str, Any]:
    """The organizations billed to the user's email address."""
    billing = BillingRepositoryManager(repos.db)
    return {
        "billed_organizations": [
            {
                "organization_id": account.organization_id,
                "billing_email": account.billing_email,
            }
            for account in await billing.billing_account.list_billed_to(email)
        ]
    }
