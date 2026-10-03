"""Password sign-in lockout per email address (login_throttle)."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from src.platform.core.config import settings
from src.platform.models.login_throttle import LoginThrottle
from src.platform.repositories.repository_manager import RepositoryManager
from tests.conftest import TestSessionLocal

ADMIN = "admin@example.org"
MAX = settings.login_max_failed_attempts


def _login(client: TestClient, email: str, password: str):
    return client.post(
        "v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def _fail(client: TestClient, email: str, times: int) -> None:
    for _ in range(times):
        response = _login(client, email, "wrong-password")
        assert response.status_code == 401
        assert response.json()["error_code"] == "login_failed"


async def _throttle(email: str) -> LoginThrottle | None:
    async with TestSessionLocal() as session:
        rs = await session.execute(
            select(LoginThrottle).where(LoginThrottle.email == email),
        )
        return rs.scalar_one_or_none()


def test_repeated_failures_lock_the_address_even_for_the_right_password(
    client: TestClient,
) -> None:
    _fail(client, ADMIN, MAX)

    response = _login(client, ADMIN, "password")
    assert response.status_code == 429
    assert response.json()["error_code"] == "login_locked"
    assert 0 < int(response.headers["Retry-After"]) <= settings.login_lockout_seconds


def test_an_address_without_an_account_locks_the_same_way(client: TestClient) -> None:
    """The lockout must not reveal which addresses have accounts."""
    _fail(client, "nobody@example.org", MAX)

    response = _login(client, "nobody@example.org", "anything")
    assert response.status_code == 429
    assert response.json()["error_code"] == "login_locked"


def test_the_address_is_matched_case_insensitively(client: TestClient) -> None:
    _fail(client, "Admin@Example.org", MAX)
    assert _login(client, ADMIN, "password").status_code == 429


def test_one_locked_address_does_not_affect_others(client: TestClient) -> None:
    _fail(client, "nobody@example.org", MAX)
    assert _login(client, ADMIN, "password").status_code == 200


def test_a_successful_sign_in_clears_earlier_failures(client: TestClient) -> None:
    _fail(client, ADMIN, MAX - 1)
    assert _login(client, ADMIN, "password").status_code == 200
    _fail(client, ADMIN, MAX - 1)
    assert _login(client, ADMIN, "password").status_code == 200


async def test_failures_older_than_the_window_do_not_count(client: TestClient) -> None:
    _fail(client, ADMIN, MAX - 1)
    async with TestSessionLocal() as session, session.begin():
        await session.execute(
            update(LoginThrottle)
            .where(LoginThrottle.email == ADMIN)
            .values(
                last_failed_at=datetime.now(UTC)
                - timedelta(seconds=settings.login_lockout_seconds + 1),
            ),
        )

    _fail(client, ADMIN, 1)  # would be the locking failure inside the window
    assert _login(client, ADMIN, "password").status_code == 200


async def test_the_lock_expires(client: TestClient) -> None:
    _fail(client, ADMIN, MAX)
    async with TestSessionLocal() as session, session.begin():
        await session.execute(
            update(LoginThrottle)
            .where(LoginThrottle.email == ADMIN)
            .values(locked_until=datetime.now(UTC) - timedelta(seconds=1)),
        )

    assert _login(client, ADMIN, "password").status_code == 200


async def test_expired_records_are_purged_and_active_ones_kept() -> None:
    window = timedelta(seconds=settings.login_lockout_seconds)
    now = datetime.now(UTC)
    async with TestSessionLocal() as session, session.begin():
        session.add_all(
            [
                LoginThrottle(
                    email="old@example.org",
                    failed_attempts=2,
                    last_failed_at=now - window - timedelta(minutes=1),
                ),
                LoginThrottle(
                    email="recent@example.org",
                    failed_attempts=2,
                    last_failed_at=now,
                ),
                LoginThrottle(
                    email="locked@example.org",
                    failed_attempts=0,
                    last_failed_at=now - window - timedelta(minutes=1),
                    locked_until=now + timedelta(minutes=5),
                ),
            ],
        )

    async with TestSessionLocal() as session, session.begin():
        purged = await RepositoryManager(session).login_throttle.purge_expired(window)

    assert purged == 1
    assert await _throttle("old@example.org") is None
    assert await _throttle("recent@example.org") is not None
    assert await _throttle("locked@example.org") is not None
