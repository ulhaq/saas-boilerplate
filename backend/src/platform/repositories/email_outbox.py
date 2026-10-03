from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.email_outbox import EmailOutbox


class EmailOutboxRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def enqueue(
        self,
        *,
        address: str,
        user_name: str,
        email_template: str,
        locale: str | None,
        data: dict[str, Any],
    ) -> EmailOutbox:
        email = EmailOutbox(
            address=address,
            user_name=user_name,
            email_template=email_template,
            locale=locale,
            data=data,
        )
        self.db.add(email)
        await self.db.flush()
        return email

    async def claim_due(self, limit: int, max_attempts: int) -> Sequence[EmailOutbox]:
        """Unsent emails due for an attempt, locked for this transaction.
        SKIP LOCKED: concurrent workers each claim different emails."""
        stmt = (
            select(EmailOutbox)
            .where(
                EmailOutbox.sent_at.is_(None),
                EmailOutbox.attempts < max_attempts,
                EmailOutbox.next_attempt_at <= datetime.now(UTC),
            )
            .order_by(EmailOutbox.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rs = await self.db.execute(stmt)
        return rs.scalars().all()

    async def mark_sent(self, email: EmailOutbox) -> None:
        email.sent_at = datetime.now(UTC)
        email.attempts += 1
        await self.db.flush()

    async def mark_failed(
        self,
        email: EmailOutbox,
        error: str,
        retry_at: datetime,
    ) -> None:
        email.attempts += 1
        email.last_error = error
        email.next_attempt_at = retry_at
        await self.db.flush()
