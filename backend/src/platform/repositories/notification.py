from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.notification import Notification
from src.platform.repositories.abc import RepositoryABC


class NotificationRepository(RepositoryABC[Notification]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Notification, db)

    async def create(
        self,
        *,
        user_id: int,
        organization_id: int,
        type: str,
        payload: dict[str, Any],
    ) -> Notification:
        instance = Notification(
            user_id=user_id,
            organization_id=organization_id,
            type=type,
            payload=payload,
        )
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def list_for_user(
        self,
        user_id: int,
        organization_id: int,
        page_size: int,
        page_number: int,
    ) -> tuple[Sequence[Notification], int]:
        stmt = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
            )
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset((page_number - 1) * page_size)
            .limit(page_size)
        )
        rs = await self.db.execute(stmt)
        items = rs.scalars().all()

        count_stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
            )
        )
        count_rs = await self.db.execute(count_stmt)
        total = int(count_rs.scalar_one())

        return items, total

    async def count_unread(self, user_id: int, organization_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.read_at.is_(None),
            )
        )
        rs = await self.db.execute(stmt)
        return int(rs.scalar_one())

    async def get(self, notification_id: int) -> Notification | None:
        stmt = select(Notification).where(Notification.id == notification_id)
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()

    async def mark_read(self, notification: Notification) -> Notification:
        stmt = (
            update(Notification)
            .where(Notification.id == notification.id)
            .values(read_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
        await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: int, organization_id: int) -> None:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        await self.db.execute(stmt)
