"""Tests for the notifications billing sends: each billing event notifies the
organization's subscription managers through `BILLING_NOTIFICATION_RULES`."""

from datetime import date

import pytest
from sqlalchemy import select

from src.billing.emails import BILLING_EMAIL_SUBJECTS, BILLING_NOTIFICATION_RULES
from src.billing.enums import BillingHookEvent, BillingNotificationCategory
from src.billing.repositories.manager import BillingRepositoryManager
from src.foundation.core import composition
from src.foundation.core.hooks import emit
from src.foundation.models.email_outbox import EmailOutbox
from src.foundation.models.notification import Notification
from src.foundation.models.user_organization import UserOrganization
from tests.conftest import TestSessionLocal

# Seeded: in organization 1 only user 1 (Owner) can manage the subscription;
# user 2 (Member) and user 3 (no roles) can't. User 4 owns organization 2.
ADMIN, STANDARD, ADMIN2 = 1, 2, 4


async def _notifications() -> list[Notification]:
    async with TestSessionLocal() as session:
        rs = await session.execute(select(Notification).order_by(Notification.id))
        return list(rs.scalars().all())


async def _emails() -> list[EmailOutbox]:
    async with TestSessionLocal() as session:
        rs = await session.execute(select(EmailOutbox).order_by(EmailOutbox.id))
        return list(rs.scalars().all())


async def _emit(
    event: BillingHookEvent = BillingHookEvent.TRIAL_ENDED,
    **data: object,
) -> None:
    async with TestSessionLocal() as session, session.begin():
        await emit(
            event,
            repos=BillingRepositoryManager(session),
            organization_id=1,
            **data,
        )


async def _prefer(category: str, *, in_app: bool, email: bool) -> None:
    async with TestSessionLocal() as session, session.begin():
        await BillingRepositoryManager(session).notification_preference.upsert(
            user_id=ADMIN,
            category=category,
            in_app=in_app,
            email=email,
        )


# ---------------------------------------------------------------------------
# Who is notified, and with what
# ---------------------------------------------------------------------------


async def test_only_subscription_managers_are_notified():
    # Dave joins Acme without a role there: managing Globex's subscription
    # doesn't make him a manager of Acme's.
    async with TestSessionLocal() as session, session.begin():
        session.add(UserOrganization(user_id=ADMIN2, organization_id=1))

    await _emit()

    [notification] = await _notifications()
    assert (notification.user_id, notification.organization_id) == (ADMIN, 1)
    assert notification.notification_type == "billing.trial-ended"
    [email] = await _emails()
    assert email.email_template == "trial-ended"
    assert email.data["billing_url"].endswith("/settings/billing")


async def test_a_date_is_iso_in_the_app_and_localized_in_the_email():
    await _emit(
        BillingHookEvent.TRIAL_ENDING,
        trial_end_date=date(2026, 10, 15),
        has_payment_method=False,
    )

    [notification] = await _notifications()
    # The app formats the date itself and links to its own pages: no URL.
    assert notification.payload == {
        "trial_end_date": "2026-10-15",
        "has_payment_method": False,
    }
    [email] = await _emails()
    # In the recipient's locale - seeded users have the default, Danish.
    assert email.data["trial_end_date"] == "15. oktober 2026"
    assert email.data["has_payment_method"] is False


async def test_a_rolled_back_change_creates_no_notification():
    class RollbackError(Exception):
        pass

    async def notify_then_fail() -> None:
        async with TestSessionLocal() as session, session.begin():
            await emit(
                BillingHookEvent.TRIAL_ENDED,
                repos=BillingRepositoryManager(session),
                organization_id=1,
            )
            raise RollbackError

    with pytest.raises(RollbackError):
        await notify_then_fail()

    assert await _notifications() == []
    assert await _emails() == []


# ---------------------------------------------------------------------------
# Notification preferences
# ---------------------------------------------------------------------------


def test_every_billing_email_is_sent_by_a_rule_under_a_declared_category():
    categories = composition.current().notification_categories
    assert {rule.email_template for rule in BILLING_NOTIFICATION_RULES} == set(
        BILLING_EMAIL_SUBJECTS["en"],
    )
    assert {rule.event for rule in BILLING_NOTIFICATION_RULES} == set(
        BillingHookEvent,
    )
    assert {rule.category for rule in BILLING_NOTIFICATION_RULES} <= set(categories)


async def test_a_manager_can_opt_out_of_trial_notifications():
    await _prefer(BillingNotificationCategory.TRIAL, in_app=False, email=False)

    await _emit()

    assert await _notifications() == []
    assert await _emails() == []


async def test_a_failed_payment_emails_even_when_turned_off():
    await _prefer(BillingNotificationCategory.PAYMENT, in_app=False, email=False)

    await _emit(BillingHookEvent.PAYMENT_FAILED)

    assert await _notifications() == []
    [email] = await _emails()
    assert email.email_template == "payment-failed"
