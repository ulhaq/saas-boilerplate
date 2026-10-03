"""Tests for creating in-app notifications (the notification repository)."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.platform.models.notification import Notification
from src.platform.repositories.repository_manager import RepositoryManager
from tests.conftest import TestSessionLocal

# Seeded: user 1 (organization 1's Owner), user 2 (a Member of organization 1)
# and user 4 (organization 2's Owner).
ADMIN, STANDARD, ADMIN2 = 1, 2, 4


async def _notifications() -> list[Notification]:
    async with TestSessionLocal() as session:
        rs = await session.execute(select(Notification).order_by(Notification.id))
        return list(rs.scalars().all())


# ---------------------------------------------------------------------------
# NotificationRepository.create
# ---------------------------------------------------------------------------


async def test_create_stores_the_notification():
    payload = {"trial_days": 14, "nested": {"items": [1, 2]}}
    async with TestSessionLocal() as session, session.begin():
        created = await RepositoryManager(session).notification.create(
            user_id=ADMIN,
            organization_id=1,
            type="billing.trial-available",
            payload=payload,
        )
        assert created.id is not None
        assert created.created_at is not None
        assert created.read_at is None

    [stored] = await _notifications()
    assert (stored.user_id, stored.organization_id) == (ADMIN, 1)
    assert stored.type == "billing.trial-available"
    assert stored.payload == payload


async def test_a_notification_is_only_visible_to_its_user_and_organization():
    async with TestSessionLocal() as session, session.begin():
        repo = RepositoryManager(session).notification
        for user_id, organization_id in [(ADMIN, 1), (STANDARD, 1), (ADMIN2, 2)]:
            await repo.create(
                user_id=user_id, organization_id=organization_id, type="t", payload={}
            )

    async with TestSessionLocal() as session:
        repo = RepositoryManager(session).notification
        items, total = await repo.list_for_user(ADMIN, 1, page_size=20, page_number=1)
        assert [(n.user_id, n.organization_id) for n in items] == [(ADMIN, 1)]
        assert total == 1
        assert await repo.count_unread(ADMIN, 1) == 1
        assert await repo.count_unread(ADMIN2, 1) == 0
        assert await repo.count_unread(ADMIN2, 2) == 1


async def test_create_rejects_an_unknown_user():
    with pytest.raises(IntegrityError):
        async with TestSessionLocal() as session, session.begin():
            await RepositoryManager(session).notification.create(
                user_id=999_999, organization_id=1, type="t", payload={}
            )
    assert await _notifications() == []
