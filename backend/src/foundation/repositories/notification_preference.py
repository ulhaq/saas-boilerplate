from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.foundation.models.notification_preference import NotificationPreference


class NotificationPreferenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(self, user_id: int) -> list[NotificationPreference]:
        rs = await self.db.execute(
            select(NotificationPreference)
            .where(NotificationPreference.user_id == user_id)
            .order_by(NotificationPreference.category),
        )
        return list(rs.scalars().all())

    async def get(self, user_id: int, category: str) -> NotificationPreference | None:
        return await self.db.get(NotificationPreference, (user_id, category))

    async def upsert(
        self,
        *,
        user_id: int,
        category: str,
        in_app: bool,
        email: bool,
    ) -> None:
        stmt = insert(NotificationPreference).values(
            user_id=user_id,
            category=category,
            in_app=in_app,
            email=email,
        )
        await self.db.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    NotificationPreference.user_id,
                    NotificationPreference.category,
                ],
                set_={
                    "in_app": stmt.excluded.in_app,
                    "email": stmt.excluded.email,
                    "updated_at": stmt.excluded.updated_at,
                },
            ),
        )
