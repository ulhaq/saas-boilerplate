"""Tests for the email outbox (services/email_outbox.py)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from src.platform.models.email_outbox import EmailOutbox
from src.platform.models.notification import Notification
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.services.billing import WebhookService
from src.platform.services.email_outbox import (
    MAX_ATTEMPTS,
    deliver_due_emails,
    queue_email,
)
from tests.conftest import TestSessionLocal


async def _queue(address: str = "a@example.org") -> None:
    async with TestSessionLocal() as session, session.begin():
        await queue_email(
            RepositoryManager(session),
            address=address,
            user_name="A",
            email_template="payment-failed",
            locale="en",
            data={"billing_url": "https://app.test/settings/billing"},
        )


async def _outbox() -> list[EmailOutbox]:
    async with TestSessionLocal() as session:
        rs = await session.execute(select(EmailOutbox).order_by(EmailOutbox.id))
        return list(rs.scalars().all())


async def _manager_ids() -> set[int]:
    """Members of organization 1 allowed to manage its subscription."""
    async with TestSessionLocal() as session:
        org = await RepositoryManager(session).organization.get(1)
        assert org
        return {
            u.id
            for u in org.users
            if any(
                p.name == "manage:subscription" for r in u.roles for p in r.permissions
            )
        }


async def _deliver() -> int:
    async with TestSessionLocal() as session, session.begin():
        return await deliver_due_emails(RepositoryManager(session))


async def test_a_rolled_back_transaction_sends_nothing():
    class Rollback(Exception):
        pass

    with pytest.raises(Rollback):
        async with TestSessionLocal() as session, session.begin():
            await queue_email(
                RepositoryManager(session),
                address="a@example.org",
                user_name="A",
                email_template="payment-failed",
                locale="en",
                data={},
            )
            raise Rollback

    assert await _outbox() == []


async def test_queued_emails_are_sent_once(mocker):
    send = mocker.patch("src.platform.services.email_outbox.send_email")
    await _queue()

    assert await _deliver() == 1
    assert await _deliver() == 0

    send.assert_called_once()
    assert send.call_args.kwargs["address"] == "a@example.org"
    assert send.call_args.kwargs["email_template"] == "payment-failed"
    assert send.call_args.kwargs["data"] == {
        "billing_url": "https://app.test/settings/billing"
    }
    [email] = await _outbox()
    assert email.sent_at is not None


async def test_a_failed_send_is_retried_later(mocker):
    mocker.patch(
        "src.platform.services.email_outbox.send_email",
        side_effect=OSError("mail server down"),
    )
    await _queue()

    assert await _deliver() == 0
    [email] = await _outbox()
    assert email.sent_at is None
    assert email.attempts == 1
    assert email.last_error == "mail server down"
    assert email.next_attempt_at > datetime.now(UTC)
    # Backing off: not due again yet.
    assert await _deliver() == 0
    assert (await _outbox())[0].attempts == 1


async def test_an_email_is_given_up_after_max_attempts(mocker):
    send = mocker.patch("src.platform.services.email_outbox.send_email")
    await _queue()
    async with TestSessionLocal() as session, session.begin():
        email = (await session.execute(select(EmailOutbox))).scalar_one()
        email.attempts = MAX_ATTEMPTS

    assert await _deliver() == 0
    send.assert_not_called()


async def test_concurrent_senders_claim_different_emails():
    await _queue("first@example.org")
    await _queue("second@example.org")

    async with TestSessionLocal() as first, first.begin():
        claimed = await RepositoryManager(first).email_outbox.claim_due(1, 5)
        claimed_first = [e.address for e in claimed]
        async with TestSessionLocal() as second, second.begin():
            claimed = await RepositoryManager(second).email_outbox.claim_due(5, 5)
            claimed_second = [e.address for e in claimed]

    assert claimed_first == ["first@example.org"]
    assert claimed_second == ["second@example.org"]


async def test_a_webhook_queues_its_email_instead_of_sending_it(
    mocker, mock_billing_provider
):
    send = mocker.patch("src.platform.services.email_outbox.send_email")
    async with TestSessionLocal() as session, session.begin():
        repos = RepositoryManager(session)
        sub = await repos.subscription.get_active_for_organization(1)
        assert sub
        await repos.subscription.update(sub, external_subscription_id="sub_paid")

    async with TestSessionLocal() as session, session.begin():
        service = WebhookService(RepositoryManager(session), mock_billing_provider)
        raw = {"data": {"object": {"subscription": "sub_paid"}}}
        await service._dispatch("invoice.payment_failed", raw)

    send.assert_not_called()
    queued = await _outbox()
    assert queued
    assert {e.email_template for e in queued} == {"payment-failed"}
    assert all(e.sent_at is None for e in queued)

    # Each emailed manager also gets an in-app notification, in the same
    # transaction - with no absolute URLs (the app links to its own pages).
    async with TestSessionLocal() as session:
        rs = await session.execute(select(Notification))
        notifications = rs.scalars().all()
    assert {(n.user_id, n.organization_id) for n in notifications} == {
        (e_user_id, 1) for e_user_id in await _manager_ids()
    }
    assert {n.type for n in notifications} == {"billing.payment-failed"}
    assert all("billing_url" not in n.payload for n in notifications)
