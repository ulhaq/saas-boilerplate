"""Billing webhooks queue their emails in the foundation's outbox."""

from sqlalchemy import select

from src.billing.repositories.manager import BillingRepositoryManager
from src.billing.services import WebhookService
from src.foundation.models.email_outbox import EmailOutbox
from src.foundation.models.notification import Notification
from src.foundation.repositories.repository_manager import RepositoryManager
from tests.conftest import TestSessionLocal


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


async def test_a_webhook_queues_its_email_instead_of_sending_it(
    mocker,
    mock_billing_provider,
):
    send = mocker.patch("src.foundation.services.email_outbox.send_email")
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        sub = await repos.subscription.get_active_for_organization(1)
        assert sub
        await repos.subscription.update(sub, external_subscription_id="sub_paid")

    async with TestSessionLocal() as session, session.begin():
        service = WebhookService(
            BillingRepositoryManager(session),
            mock_billing_provider,
        )
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
    assert {n.notification_type for n in notifications} == {"billing.payment-failed"}
    assert all("billing_url" not in n.payload for n in notifications)
