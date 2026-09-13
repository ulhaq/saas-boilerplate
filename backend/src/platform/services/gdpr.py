import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.core.audit import write_audit_log
from src.platform.core.config import settings
from src.platform.enums import AuditAction
from src.platform.models.email_verification_token import EmailVerificationToken
from src.platform.models.invite_token import InviteToken
from src.platform.models.organization import Organization
from src.platform.models.password_reset_token import PasswordResetToken
from src.platform.models.refresh_token import RefreshToken
from src.platform.models.user import User

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
    invite_cutoff = now - timedelta(seconds=settings.invite_expiry) - cutoff_buffer

    r1 = await db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.created_at < password_reset_cutoff
        )
    )
    r2 = await db.execute(
        delete(EmailVerificationToken).where(
            EmailVerificationToken.created_at < email_verify_cutoff
        )
    )
    r3 = await db.execute(
        delete(InviteToken).where(InviteToken.created_at < invite_cutoff)
    )
    # Refresh-token rows carry their own expiry; one row per session/device,
    # so expired sessions accumulate until purged here.
    r4 = await db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at < now - cutoff_buffer)
    )
    return (
        cast(CursorResult[Any], r1).rowcount
        + cast(CursorResult[Any], r2).rowcount
        + cast(CursorResult[Any], r3).rowcount
        + cast(CursorResult[Any], r4).rowcount
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
    while True:
        try:
            async with session_factory() as session:
                async with session.begin():
                    token_count = await purge_expired_tokens(session)
                    user_count = await purge_soft_deleted_users(session)
                    org_count = await purge_soft_deleted_orgs(session)
                    log.info(
                        "GDPR retention: purged %d token(s), %d user(s), %d org(s)",
                        token_count,
                        user_count,
                        org_count,
                    )
        except Exception as exc:
            log.error("GDPR retention loop error: %s", exc, exc_info=True)
        await asyncio.sleep(settings.gdpr_retention_interval_seconds)
