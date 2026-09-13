from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.waitlist_entry import WaitlistEntry


class WaitlistEntryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> WaitlistEntry | None:
        stmt = select(WaitlistEntry).where(WaitlistEntry.email == email)
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()

    async def create(self, email: str, name: str | None = None) -> WaitlistEntry:
        record = WaitlistEntry(email=email, name=name)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record
