"""Tests for the in-app notifications billing writes alongside its emails
(`notify_subscription_managers`)."""

from datetime import date

import pytest
from sqlalchemy import select

from src.billing.repositories.manager import BillingRepositoryManager
from src.billing.services.common import notify_subscription_managers
from src.platform.models.notification import Notification
from tests.conftest import TestSessionLocal

# Seeded: in organization 1 only user 1 (Owner) can manage the subscription;
# user 2 (Member) and user 3 (no roles) can't. User 4 owns organization 2.
ADMIN, STANDARD, ADMIN2 = 1, 2, 4


async def _notifications() -> list[Notification]:
    async with TestSessionLocal() as session:
        rs = await session.execute(select(Notification).order_by(Notification.id))
        return list(rs.scalars().all())


# ---------------------------------------------------------------------------
# notify_subscription_managers - the billing notifications it writes
# ---------------------------------------------------------------------------


async def _notify(data: dict) -> int:
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        organization = await repos.organization.get(1)
        assert organization
        return await notify_subscription_managers(
            repos,
            organization,
            "trial-ending",
            data,
        )


async def test_only_subscription_managers_are_notified():
    assert await _notify({}) == 1

    [notification] = await _notifications()
    assert (notification.user_id, notification.organization_id) == (ADMIN, 1)
    assert notification.notification_type == "billing.trial-ending"


async def test_the_notification_payload_is_json_safe():
    await _notify(
        {
            "trial_end_date": date(2026, 10, 15),
            "trial_days": 14,
            "has_payment_method": False,
            "billing_url": "https://app.test/settings/billing",
        },
    )

    [notification] = await _notifications()
    # Dates as ISO strings (the app formats them per locale); no absolute URLs.
    assert notification.payload == {
        "trial_end_date": "2026-10-15",
        "trial_days": 14,
        "has_payment_method": False,
    }


async def test_a_rolled_back_change_creates_no_notification():
    class RollbackError(Exception):
        pass

    async def notify_then_fail() -> None:
        async with TestSessionLocal() as session, session.begin():
            repos = BillingRepositoryManager(session)
            organization = await repos.organization.get(1)
            assert organization
            await notify_subscription_managers(repos, organization, "trial-ending", {})
            raise RollbackError

    with pytest.raises(RollbackError):
        await notify_then_fail()

    assert await _notifications() == []
