"""Tests for the email outbox (services/email_outbox.py)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from src.foundation.models.email_outbox import EmailOutbox
from src.foundation.repositories.repository_manager import RepositoryManager
from src.foundation.services.email_outbox import (
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


async def _deliver() -> int:
    async with TestSessionLocal() as session, session.begin():
        return await deliver_due_emails(RepositoryManager(session))


async def test_a_rolled_back_transaction_sends_nothing():
    class RollbackError(Exception):
        pass

    async def queue_then_fail() -> None:
        async with TestSessionLocal() as session, session.begin():
            await queue_email(
                RepositoryManager(session),
                address="a@example.org",
                user_name="A",
                email_template="payment-failed",
                locale="en",
                data={},
            )
            raise RollbackError

    with pytest.raises(RollbackError):
        await queue_then_fail()

    assert await _outbox() == []


async def test_queued_emails_are_sent_once(mocker):
    send = mocker.patch("src.foundation.services.email_outbox.send_email")
    await _queue()

    assert await _deliver() == 1
    assert await _deliver() == 0

    send.assert_called_once()
    assert send.call_args.kwargs["address"] == "a@example.org"
    assert send.call_args.kwargs["email_template"] == "payment-failed"
    assert send.call_args.kwargs["data"] == {
        "billing_url": "https://app.test/settings/billing",
    }
    [email] = await _outbox()
    assert email.sent_at is not None


async def test_a_failed_send_is_retried_later(mocker):
    mocker.patch(
        "src.foundation.services.email_outbox.send_email",
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
    send = mocker.patch("src.foundation.services.email_outbox.send_email")
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
