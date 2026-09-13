"""Unit tests for GDPR utility functions."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from src.platform.services.gdpr import (
    purge_expired_tokens,
    purge_soft_deleted_orgs,
    purge_soft_deleted_users,
    run_gdpr_retention_loop,
)
from tests.conftest import TestSessionLocal


async def test_purge_expired_tokens_removes_old_records():
    from src.platform.core.security import hash_secret
    from src.platform.models.email_verification_token import EmailVerificationToken
    from src.platform.models.invite_token import InviteToken
    from src.platform.models.password_reset_token import PasswordResetToken

    very_old = datetime.now(UTC) - timedelta(days=400)

    async with TestSessionLocal() as session:
        async with session.begin():
            # Seed old tokens directly
            session.add(
                EmailVerificationToken(
                    email="old_ev@example.com",
                    token=hash_secret("tok1"),
                    created_at=very_old,
                )
            )
            session.add(
                PasswordResetToken(
                    user_id=1,
                    token=hash_secret("tok2"),
                    created_at=very_old,
                )
            )
            session.add(
                InviteToken(
                    email="old_inv@example.com",
                    token=hash_secret("tok3"),
                    created_at=very_old,
                )
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            count = await purge_expired_tokens(session)

    assert count >= 3


async def test_purge_expired_tokens_keeps_fresh_records():
    from src.platform.core.security import hash_secret

    async with TestSessionLocal() as session:
        async with session.begin():
            # A fresh email verification token should NOT be purged
            from src.platform.models.email_verification_token import (
                EmailVerificationToken,
            )

            session.add(
                EmailVerificationToken(
                    email="fresh@example.com",
                    token=hash_secret("fresh_tok"),
                )
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            count = await purge_expired_tokens(session)

    # The fresh token should not have been purged
    assert count == 0


async def test_purge_soft_deleted_users_removes_old():
    from sqlalchemy import select

    from src.platform.core.security import hash_secret
    from src.platform.models.user import User

    very_old = datetime.now(UTC) - timedelta(days=400)

    async with TestSessionLocal() as session:
        async with session.begin():
            user = User(
                name="Deleted Old",
                email="deleted_old@example.com",
                password=hash_secret("pass"),
                deleted_at=very_old,
            )
            session.add(user)
            await session.flush()
            user_id = user.id

    async with TestSessionLocal() as session:
        async with session.begin():
            count = await purge_soft_deleted_users(session)

    assert count >= 1

    async with TestSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        assert result.scalar_one_or_none() is None


async def test_purge_soft_deleted_users_keeps_recent():
    from src.platform.core.security import hash_secret
    from src.platform.models.user import User

    recent = datetime.now(UTC) - timedelta(days=10)

    async with TestSessionLocal() as session:
        async with session.begin():
            user = User(
                name="Deleted Recent",
                email="deleted_recent@example.com",
                password=hash_secret("pass"),
                deleted_at=recent,
            )
            session.add(user)

    async with TestSessionLocal() as session:
        async with session.begin():
            count = await purge_soft_deleted_users(session)

    assert count == 0


async def test_purge_soft_deleted_orgs_removes_old():
    from sqlalchemy import select

    from src.platform.models.organization import Organization

    very_old = datetime.now(UTC) - timedelta(days=400)

    async with TestSessionLocal() as session:
        async with session.begin():
            org = Organization(
                name="Old Deleted Org",
                deleted_at=very_old,
                billing_email="billing@example.org",
            )
            session.add(org)
            await session.flush()
            org_id = org.id

    async with TestSessionLocal() as session:
        async with session.begin():
            count = await purge_soft_deleted_orgs(session)

    assert count >= 1

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(Organization).where(Organization.id == org_id)
        )
        assert result.scalar_one_or_none() is None


async def test_purge_soft_deleted_orgs_keeps_recent():
    from src.platform.models.organization import Organization

    recent = datetime.now(UTC) - timedelta(days=10)

    async with TestSessionLocal() as session:
        async with session.begin():
            org = Organization(
                name="Recent Deleted Org",
                deleted_at=recent,
                billing_email="billing@example.org",
            )
            session.add(org)

    async with TestSessionLocal() as session:
        async with session.begin():
            count = await purge_soft_deleted_orgs(session)

    assert count == 0


async def test_purge_soft_deleted_orgs_ignores_active():
    from src.platform.models.organization import Organization

    async with TestSessionLocal() as session:
        async with session.begin():
            org = Organization(name="Active Org", billing_email="billing@example.org")
            session.add(org)

    async with TestSessionLocal() as session:
        async with session.begin():
            count = await purge_soft_deleted_orgs(session)

    assert count == 0


# ---------------------------------------------------------------------------
# run_gdpr_retention_loop
# ---------------------------------------------------------------------------


async def test_run_gdpr_retention_loop_runs_one_iteration(mocker):
    """Loop sleeps, runs cleanup, then exits on the second sleep via CancelledError."""
    call_count = 0

    async def mock_sleep(_delay):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    mocker.patch("src.platform.services.gdpr.asyncio.sleep", side_effect=mock_sleep)

    with pytest.raises(asyncio.CancelledError):
        await run_gdpr_retention_loop(TestSessionLocal)

    assert call_count >= 2


async def test_run_gdpr_retention_loop_swallows_exceptions(mocker):
    """Exceptions inside the cleanup body are caught and logged; loop continues."""
    call_count = 0

    async def mock_sleep(_delay):
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            raise asyncio.CancelledError()

    mocker.patch("src.platform.services.gdpr.asyncio.sleep", side_effect=mock_sleep)
    mocker.patch(
        "src.platform.services.gdpr.purge_expired_tokens",
        side_effect=RuntimeError("db gone"),
    )

    with pytest.raises(asyncio.CancelledError):
        await run_gdpr_retention_loop(TestSessionLocal)

    assert call_count >= 3
