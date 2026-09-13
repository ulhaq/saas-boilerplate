from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.invite_token import InviteToken


class InviteTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> InviteToken | None:
        stmt = select(InviteToken).where(InviteToken.email == email)
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()

    async def create(self, email: str, token: str) -> InviteToken:
        record = InviteToken(email=email, token=token)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete_by_email(self, email: str) -> None:
        stmt = delete(InviteToken).where(InviteToken.email == email)
        await self.db.execute(stmt)
        await self.db.flush()
