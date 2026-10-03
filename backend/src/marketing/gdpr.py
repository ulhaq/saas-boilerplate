"""Marketing's share of a user's data export (GDPR)."""

from typing import Any

from src.marketing.repositories.manager import MarketingRepositoryManager
from src.platform.repositories.repository_manager import RepositoryManager


async def export_user_data(
    *,
    repos: RepositoryManager,
    user_id: int,  # noqa: ARG001 - part of the exporter signature
    email: str,
) -> dict[str, Any]:
    """The user's waitlist sign-up, if they made one."""
    marketing = MarketingRepositoryManager(repos.db)
    entry = await marketing.waitlist_entry.get_by_email(email)
    return {
        "waitlist": (
            {
                "email": entry.email,
                "name": entry.name,
                "created_at": entry.created_at.isoformat(),
            }
            if entry
            else None
        ),
    }
