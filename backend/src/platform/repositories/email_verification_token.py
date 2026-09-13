from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.email_verification_token import EmailVerificationToken


class EmailVerificationTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> EmailVerificationToken | None:
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.email == email
        )
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()

    async def create(
        self, email: str, token: str, terms_accepted_at: datetime | None = None
    ) -> EmailVerificationToken:
        record = EmailVerificationToken(
            email=email, token=token, terms_accepted_at=terms_accepted_at
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete_by_email(self, email: str) -> None:
        stmt = delete(EmailVerificationToken).where(
            EmailVerificationToken.email == email
        )
        await self.db.execute(stmt)
        await self.db.flush()
