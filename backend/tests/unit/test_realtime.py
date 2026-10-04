"""Tests for realtime events: `after_commit`, the brokers, publishing
notification events and the event stream (`EventStreamService`)."""

import dataclasses
from enum import StrEnum

import pytest

from src.foundation.core import composition, realtime
from src.foundation.core.database import after_commit, drain_after_commit
from src.foundation.core.module import NotificationCategory
from src.foundation.core.realtime import (
    RESYNC,
    LocalBroker,
    RealtimeEvent,
    RedisBroker,
    publish_to_user,
    user_channel,
)
from src.foundation.core.security import Auth
from src.foundation.enums import NotificationEvent
from src.foundation.repositories.repository_manager import RepositoryManager
from src.foundation.services.notification import deliver_notification
from src.foundation.services.realtime import READY_EVENT, EventStreamService
from tests.conftest import TestSessionLocal

# Seeded: user 1 is organization 1's Owner.
ADMIN = 1
EVENT = RealtimeEvent(type="test.changed", organization_id=1, data={"id": 7})


class Category(StrEnum):
    NEWS = "test.news"


@pytest.fixture
def test_category(monkeypatch):
    installed = dataclasses.replace(
        composition.current(),
        notification_categories={
            Category.NEWS: NotificationCategory(key=Category.NEWS, email=False),
        },
    )
    monkeypatch.setattr(composition, "current", lambda: installed)


# ---------------------------------------------------------------------------
# after_commit
# ---------------------------------------------------------------------------


async def test_after_commit_runs_the_callback_once_committed():
    ran: list[str] = []

    async def callback() -> None:
        ran.append("ran")

    async with TestSessionLocal() as session, session.begin():
        after_commit(session, callback)
        await drain_after_commit()
        assert ran == []
    await drain_after_commit()
    assert ran == ["ran"]


async def test_after_commit_drops_the_callback_on_rollback():
    ran: list[str] = []

    async def callback() -> None:
        ran.append("ran")

    async def write_then_fail() -> None:
        async with TestSessionLocal() as session, session.begin():
            after_commit(session, callback)
            raise RuntimeError

    with pytest.raises(RuntimeError):
        await write_then_fail()
    async with TestSessionLocal() as session, session.begin():
        pass  # a later transaction on a new session doesn't run it either
    await drain_after_commit()
    assert ran == []


async def test_a_failing_after_commit_callback_is_logged_not_raised(caplog):
    async def callback() -> None:
        raise ValueError("boom")

    async with TestSessionLocal() as session, session.begin():
        after_commit(session, callback)
    await drain_after_commit()
    assert "After-commit callback" in caplog.text


# ---------------------------------------------------------------------------
# Brokers
# ---------------------------------------------------------------------------


async def test_an_event_reaches_only_its_channels_subscribers():
    broker = LocalBroker()
    async with (
        broker.subscribe(user_channel(1)) as mine,
        broker.subscribe(user_channel(2)) as other,
    ):
        await broker.publish(user_channel(1), EVENT)
        assert await mine.next(wait=0.1) == EVENT
        assert await other.next(wait=0.01) is None


async def test_a_subscriber_that_falls_behind_is_told_to_resync():
    broker = LocalBroker()
    async with broker.subscribe(user_channel(1)) as subscription:
        for _ in range(500):
            await broker.publish(user_channel(1), EVENT)
        assert await subscription.next(wait=0.1) == RESYNC


def test_an_event_survives_its_wire_format():
    assert RealtimeEvent.from_json(EVENT.to_json()) == EVENT


async def test_the_redis_relay_hands_events_to_local_subscribers():
    broker = RedisBroker("redis://localhost:1")  # never connects
    with broker._fanout.subscribe(user_channel(1)) as subscription:
        broker._relay_message(
            {
                "type": "pmessage",
                "channel": b"realtime:user:1",
                "data": EVENT.to_json().encode(),
            },
        )
        broker._relay_message(
            {"type": "pmessage", "channel": b"realtime:user:1", "data": b"{oops"},
        )
        assert await subscription.next(wait=0.1) == EVENT
        assert await subscription.next(wait=0.01) is None
    await broker.close()


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------


async def test_publish_to_user_sends_after_commit(realtime_broker: LocalBroker):
    async with realtime_broker.subscribe(user_channel(ADMIN)) as subscription:
        async with TestSessionLocal() as session, session.begin():
            publish_to_user(session, ADMIN, EVENT)
            await drain_after_commit()
            assert await subscription.next(wait=0.01) is None
        await drain_after_commit()
        assert await subscription.next(wait=0.1) == EVENT


async def _deliver(*, roll_back: bool = False) -> None:
    async with TestSessionLocal() as session, session.begin():
        repos = RepositoryManager(session)
        user = await repos.user.unscoped.get(ADMIN)
        assert user
        await deliver_notification(
            repos,
            user=user,
            organization_id=1,
            category=Category.NEWS,
            notification_type="test.thing",
            payload={},
            email_template="welcome",
            email_data={},
        )
        if roll_back:
            raise RuntimeError


@pytest.mark.usefixtures("test_category")
async def test_an_in_app_notification_is_announced(realtime_broker: LocalBroker):
    async with realtime_broker.subscribe(user_channel(ADMIN)) as subscription:
        await _deliver()
        await drain_after_commit()
        event = await subscription.next(wait=0.1)
    assert event is not None
    assert event.type == NotificationEvent.CREATED
    assert event.organization_id == 1
    assert event.data["notification_type"] == "test.thing"


@pytest.mark.usefixtures("test_category")
async def test_a_rolled_back_notification_is_not_announced(
    realtime_broker: LocalBroker,
):
    async with realtime_broker.subscribe(user_channel(ADMIN)) as subscription:
        with pytest.raises(RuntimeError):
            await _deliver(roll_back=True)
        await drain_after_commit()
        assert await subscription.next(wait=0.05) is None


# ---------------------------------------------------------------------------
# EventStreamService
# ---------------------------------------------------------------------------


def _service(organization_id: int = 1) -> EventStreamService:
    return EventStreamService(
        Auth(
            id=ADMIN,
            name="Admin",
            email="admin@example.org",
            organization_id=organization_id,
            roles=[],
            permissions=[],
        ),
    )


async def test_the_stream_starts_ready_and_forwards_the_current_organizations_events(
    realtime_broker: LocalBroker,
):
    stream = _service().stream()
    assert await anext(stream) == f"event: {READY_EVENT}\ndata: {{}}\n\n"

    channel = user_channel(ADMIN)
    other_org = dataclasses.replace(EVENT, organization_id=2)
    await realtime_broker.publish(channel, other_org)
    await realtime_broker.publish(channel, EVENT)
    await realtime_broker.publish(channel, RESYNC)

    assert await anext(stream) == f"event: test.changed\ndata: {EVENT.to_json()}\n\n"
    assert await anext(stream) == f"event: resync\ndata: {RESYNC.to_json()}\n\n"
    await stream.aclose()


async def test_an_idle_stream_sends_keep_alives_and_ends(monkeypatch):
    monkeypatch.setattr(realtime.settings, "realtime_heartbeat_seconds", 0.05)
    monkeypatch.setattr(realtime.settings, "realtime_stream_max_seconds", 0.12)
    messages = [message async for message in _service().stream()]
    assert messages[0].startswith(f"event: {READY_EVENT}")
    assert messages[1:] == [": keep-alive\n\n"] * len(messages[1:])
    assert 2 <= len(messages) <= 4
