"""Tests for notification preferences: `deliver_notification` honouring them,
and the `/v1/notifications/preferences` endpoints."""

import dataclasses
from enum import StrEnum

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.foundation.core import composition
from src.foundation.core.module import NotificationCategory
from src.foundation.enums import Permission
from src.foundation.models.email_outbox import EmailOutbox
from src.foundation.models.notification import Notification
from src.foundation.repositories.repository_manager import RepositoryManager
from src.foundation.services.notification import deliver_notification
from tests.conftest import TestSessionLocal

# Seeded: user 1 is organization 1's Owner (every permission), user 2 a Member.
ADMIN, STANDARD = 1, 2


class Category(StrEnum):
    NEWS = "test.news"
    DIGEST = "test.digest"
    CRITICAL = "test.critical"
    AUDIT = "test.audit"


class UndeclaredCategory(StrEnum):
    UNKNOWN = "test.unknown"


CATEGORIES = {
    category.key: category
    for category in [
        NotificationCategory(key=Category.NEWS),
        NotificationCategory(key=Category.DIGEST, email=False),
        NotificationCategory(key=Category.CRITICAL, email_required=True),
        NotificationCategory(
            key=Category.AUDIT,
            permission=Permission.READ_AUDIT_LOG,
        ),
    ]
}


@pytest.fixture(autouse=True)
def test_categories(monkeypatch):
    """Install test-local categories, so these tests don't depend on a module."""
    installed = dataclasses.replace(
        composition.current(),
        notification_categories=CATEGORIES,
    )
    monkeypatch.setattr(composition, "current", lambda: installed)


async def _save(user_id: int, category: StrEnum, *, in_app: bool, email: bool) -> None:
    async with TestSessionLocal() as session, session.begin():
        await RepositoryManager(session).notification_preference.upsert(
            user_id=user_id,
            category=category,
            in_app=in_app,
            email=email,
        )


async def _deliver(category: StrEnum, user_id: int = ADMIN) -> tuple[int, int]:
    """Deliver one notification; returns (in-app notifications, queued emails)."""
    async with TestSessionLocal() as session, session.begin():
        repos = RepositoryManager(session)
        user = await repos.user.unscoped.get(user_id)
        assert user
        await deliver_notification(
            repos,
            user=user,
            organization_id=1,
            category=category,
            notification_type="test.thing",
            payload={"a": 1},
            email_template="welcome",
            email_data={},
        )
    async with TestSessionLocal() as session:
        notifications = (await session.execute(select(Notification))).scalars()
        emails = (await session.execute(select(EmailOutbox))).scalars()
        return len(notifications.all()), len(emails.all())


# ---------------------------------------------------------------------------
# deliver_notification
# ---------------------------------------------------------------------------


async def test_without_a_preference_the_category_defaults_apply():
    assert await _deliver(Category.NEWS) == (1, 1)


async def test_a_category_can_default_to_no_email():
    assert await _deliver(Category.DIGEST) == (1, 0)


async def test_a_user_can_turn_off_the_email():
    await _save(ADMIN, Category.NEWS, in_app=True, email=False)
    assert await _deliver(Category.NEWS) == (1, 0)


async def test_a_user_can_turn_off_the_in_app_notification():
    await _save(ADMIN, Category.NEWS, in_app=False, email=True)
    assert await _deliver(Category.NEWS) == (0, 1)


async def test_a_preference_is_per_user():
    await _save(STANDARD, Category.NEWS, in_app=False, email=False)
    assert await _deliver(Category.NEWS, user_id=ADMIN) == (1, 1)


async def test_a_required_email_is_sent_whatever_the_preference():
    await _save(ADMIN, Category.CRITICAL, in_app=False, email=False)
    assert await _deliver(Category.CRITICAL) == (0, 1)


async def test_an_unknown_category_is_a_programming_error():
    with pytest.raises(ValueError, match=r"test\.unknown"):
        await _deliver(UndeclaredCategory.UNKNOWN)


# ---------------------------------------------------------------------------
# GET / PATCH /v1/notifications/preferences
# ---------------------------------------------------------------------------


def test_preferences_list_every_category_with_its_defaults(
    admin_authenticated: TestClient,
):
    response = admin_authenticated.get("/v1/notifications/preferences")

    assert response.status_code == 200
    assert [
        (p["category"], p["in_app"], p["email"], p["email_required"])
        for p in response.json()
    ] == [
        ("test.news", True, True, False),
        ("test.digest", True, False, False),
        ("test.critical", True, True, True),
        ("test.audit", True, True, False),
    ]


def test_a_category_is_only_offered_to_holders_of_its_permission(
    standard_authenticated: TestClient,
):
    response = standard_authenticated.get("/v1/notifications/preferences")

    assert "test.audit" not in [p["category"] for p in response.json()]


def test_updating_saves_the_listed_categories_only(admin_authenticated: TestClient):
    response = admin_authenticated.patch(
        "/v1/notifications/preferences",
        json=[{"category": "test.news", "in_app": False, "email": False}],
    )

    assert response.status_code == 200
    by_category = {p["category"]: p for p in response.json()}
    assert by_category["test.news"]["in_app"] is False
    assert by_category["test.news"]["email"] is False
    assert by_category["test.digest"]["in_app"] is True
    # Persisted.
    again = admin_authenticated.get("/v1/notifications/preferences").json()
    assert {p["category"]: p for p in again} == by_category


def test_updating_an_unknown_category_is_rejected(admin_authenticated: TestClient):
    response = admin_authenticated.patch(
        "/v1/notifications/preferences",
        json=[{"category": "test.unknown", "in_app": True, "email": True}],
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "parameter_invalid"


def test_a_required_email_cant_be_turned_off(admin_authenticated: TestClient):
    response = admin_authenticated.patch(
        "/v1/notifications/preferences",
        json=[{"category": "test.critical", "in_app": False, "email": False}],
    )

    assert response.status_code == 422
    stored = admin_authenticated.get("/v1/notifications/preferences").json()
    assert {"category": "test.critical", "in_app": True, "email": True,
            "email_required": True} in stored  # fmt: skip


def test_preferences_require_authentication(client: TestClient):
    assert client.get("/v1/notifications/preferences").status_code == 401


async def test_saved_preferences_are_in_the_data_export(
    admin_authenticated: TestClient,
):
    await _save(ADMIN, Category.NEWS, in_app=False, email=True)

    export = admin_authenticated.get("/v1/users/me/export").json()

    [preference] = export["notification_preferences"]
    assert preference["category"] == "test.news"
    assert (preference["in_app"], preference["email"]) == (False, True)
