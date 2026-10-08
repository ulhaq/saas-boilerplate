import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from src.foundation.core.config import settings
from src.foundation.core.database import try_job_lock
from src.foundation.core.telemetry import track_worker_run
from src.foundation.enums import AuditAction
from src.foundation.models.email_verification_token import EmailVerificationToken
from src.foundation.models.invitation import Invitation
from src.foundation.models.organization import Organization
from src.foundation.models.password_reset_token import PasswordResetToken
from src.foundation.models.refresh_token import RefreshToken
from src.foundation.models.user import User
from src.foundation.repositories.login_throttle import LoginThrottleRepository
from src.foundation.services.audit_log import write_audit_log

log = logging.getLogger(__name__)


async def purge_expired_tokens(db: AsyncSession) -> int:
    now = datetime.now(UTC)
    cutoff_buffer = timedelta(days=settings.gdpr_token_purge_days)

    password_reset_cutoff = (
        now - timedelta(seconds=settings.auth_password_reset_expiry) - cutoff_buffer
    )
    email_verify_cutoff = (
        now - timedelta(seconds=settings.email_verification_expiry) - cutoff_buffer
    )

    r1 = await db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.created_at < password_reset_cutoff,
        ),
    )
    r2 = await db.execute(
        delete(EmailVerificationToken).where(
            EmailVerificationToken.created_at < email_verify_cutoff,
        ),
    )
    r3 = await db.execute(
        delete(Invitation).where(Invitation.expires_at < now - cutoff_buffer),
    )
    # Refresh-token rows carry their own expiry; one row per session/device,
    # so expired sessions accumulate until purged here.
    r4 = await db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at < now - cutoff_buffer),
    )
    return (
        cast(CursorResult[Any], r1).rowcount
        + cast(CursorResult[Any], r2).rowcount
        + cast(CursorResult[Any], r3).rowcount
        + cast(CursorResult[Any], r4).rowcount
    )


async def purge_expired_login_throttles(db: AsyncSession) -> int:
    """Failed sign-in records past their lockout window (they hold email
    addresses, which may belong to no account)."""
    return await LoginThrottleRepository(db).purge_expired(
        timedelta(seconds=settings.login_lockout_seconds),
    )


async def purge_soft_deleted_users(db: AsyncSession) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=settings.gdpr_retention_days)
    stmt = select(User).where(
        User.deleted_at.is_not(None),
        User.deleted_at < cutoff,
    )
    rs = await db.execute(stmt)
    users = rs.scalars().unique().all()
    for user in users:
        await write_audit_log(
            db,
            action=AuditAction.USER_ANONYMIZE,
            resource_type="user",
            resource_id=user.id,
            details={"reason": "gdpr_retention", "email": user.email},
        )
        await db.delete(user)
    return len(users)


async def purge_soft_deleted_orgs(db: AsyncSession) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=settings.gdpr_retention_days)
    stmt = select(Organization).where(
        Organization.deleted_at.is_not(None),
        Organization.deleted_at < cutoff,
    )
    rs = await db.execute(stmt)
    orgs = rs.scalars().unique().all()
    for org in orgs:
        await write_audit_log(
            db,
            action=AuditAction.ORG_DELETE,
            resource_type="organization",
            resource_id=org.id,
            details={"reason": "gdpr_retention", "name": org.name},
        )
        await db.delete(org)
    return len(orgs)


async def run_gdpr_retention_loop(session_factory: Any) -> None:
    interval = settings.gdpr_retention_interval_seconds
    while True:
        try:
            with track_worker_run("gdpr_retention", interval):
                async with session_factory() as session, session.begin():
                    if await try_job_lock(session, "gdpr_retention"):
                        token_count = await purge_expired_tokens(session)
                        user_count = await purge_soft_deleted_users(session)
                        org_count = await purge_soft_deleted_orgs(session)
                        throttle_count = await purge_expired_login_throttles(
                            session,
                        )
                        log.info(
                            "GDPR retention: purged %d token(s), %d user(s), "
                            "%d org(s), %d login throttle(s)",
                            token_count,
                            user_count,
                            org_count,
                            throttle_count,
                        )
                    else:
                        log.info("GDPR retention: running in another worker")
        except Exception:
            log.exception("GDPR retention loop error")
        await asyncio.sleep(interval)
