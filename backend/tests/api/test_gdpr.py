from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from src.platform.models.user import User
from src.platform.services.gdpr import purge_expired_tokens, purge_soft_deleted_users
from tests.conftest import TestSessionLocal


def _do_register(client: TestClient, email: str = "purge_test@example.org") -> None:
    client.post("/v1/auth/register", json={"email": email, "terms_accepted": True})


async def test_purge_expired_tokens_removes_stale_tokens(
    mocker: MockerFixture, client: TestClient
) -> None:
    mocker.patch("src.platform.services.auth.send_email")
    _do_register(client)
    client.post("v1/auth/reset-password/request", json={"email": "admin@example.org"})

    with (
        patch("src.platform.core.config.settings.auth_password_reset_expiry", 0),
        patch("src.platform.core.config.settings.email_verification_expiry", 0),
        patch("src.platform.core.config.settings.invite_expiry", 0),
        patch("src.platform.core.config.settings.gdpr_token_purge_days", 0),
    ):
        async with TestSessionLocal() as session:
            async with session.begin():
                count = await purge_expired_tokens(session)

    assert count >= 2


async def test_purge_expired_tokens_returns_zero_when_nothing_to_purge() -> None:
    async with TestSessionLocal() as session:
        async with session.begin():
            count = await purge_expired_tokens(session)

    assert count == 0


async def test_purge_soft_deleted_users_removes_past_retention() -> None:
    async with TestSessionLocal() as session:
        user = await session.get(User, 2)
        assert user is not None
        user.deleted_at = datetime.now(UTC) - timedelta(days=1)
        await session.commit()

    with patch("src.platform.core.config.settings.gdpr_retention_days", 0):
        async with TestSessionLocal() as session:
            async with session.begin():
                count = await purge_soft_deleted_users(session)

    assert count == 1


async def test_purge_soft_deleted_users_keeps_users_within_retention() -> None:
    async with TestSessionLocal() as session:
        user = await session.get(User, 2)
        assert user is not None
        user.deleted_at = datetime.now(UTC)
        await session.commit()

    with patch("src.platform.core.config.settings.gdpr_retention_days", 30):
        async with TestSessionLocal() as session:
            async with session.begin():
                count = await purge_soft_deleted_users(session)

    assert count == 0


async def test_purge_soft_deleted_users_ignores_active_users() -> None:
    with patch("src.platform.core.config.settings.gdpr_retention_days", 0):
        async with TestSessionLocal() as session:
            async with session.begin():
                count = await purge_soft_deleted_users(session)

    assert count == 0
