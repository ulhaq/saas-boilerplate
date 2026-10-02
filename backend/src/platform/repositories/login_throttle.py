from datetime import UTC, datetime, timedelta

from sqlalchemy import case, delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.login_throttle import LoginThrottle


class LoginThrottleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def locked_until(self, email: str) -> datetime | None:
        """When the address's sign-in lock expires, if it is locked now."""
        stmt = select(LoginThrottle.locked_until).where(
            LoginThrottle.email == email,
            LoginThrottle.locked_until > datetime.now(UTC),
        )
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()

    async def record_failure(
        self, email: str, *, max_attempts: int, window: timedelta
    ) -> datetime | None:
        """Count a failed sign-in; failures older than `window` start the count
        over. Locks the address for `window` once `max_attempts` is reached and
        returns when that lock expires (else None). One upsert, so concurrent
        failures can't lose counts."""
        now = datetime.now(UTC)
        upsert = (
            insert(LoginThrottle)
            .values(email=email, failed_attempts=1, last_failed_at=now)
            .on_conflict_do_update(
                index_elements=[LoginThrottle.email],
                set_={
                    "failed_attempts": case(
                        (LoginThrottle.last_failed_at < now - window, 1),
                        else_=LoginThrottle.failed_attempts + 1,
                    ),
                    "last_failed_at": now,
                },
            )
            .returning(LoginThrottle.failed_attempts)
        )
        attempts = (await self.db.execute(upsert)).scalar_one()
        if attempts < max_attempts:
            return None
        locked_until = now + window
        await self.db.execute(
            update(LoginThrottle)
            .where(LoginThrottle.email == email)
            .values(failed_attempts=0, locked_until=locked_until)
        )
        return locked_until

    async def clear(self, email: str) -> None:
        await self.db.execute(delete(LoginThrottle).where(LoginThrottle.email == email))

    async def purge_expired(self, window: timedelta) -> int:
        """Delete rows whose failures are older than `window` and that aren't
        locked anymore."""
        now = datetime.now(UTC)
        rs = await self.db.execute(
            delete(LoginThrottle).where(
                LoginThrottle.last_failed_at < now - window,
                or_(
                    LoginThrottle.locked_until.is_(None),
                    LoginThrottle.locked_until <= now,
                ),
            )
        )
        return rs.rowcount  # ty: ignore[unresolved-attribute]
