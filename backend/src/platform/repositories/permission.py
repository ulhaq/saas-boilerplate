from abc import ABC
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.permission import Permission
from src.platform.repositories.abc import SoftDeleteRepositoryABC
from src.platform.repositories.base import SoftDeleteRepository


class PermissionRepositoryABC(SoftDeleteRepositoryABC[Permission], ABC): ...


class PermissionRepository(SoftDeleteRepository[Permission], PermissionRepositoryABC):
    search_fields: ClassVar[list[str]] = ["name", "description"]

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Permission, db)

    async def get_by_name(
        self,
        name: str,
        *,
        include_deleted: bool = False,
    ) -> Permission | None:
        return await self._get_by_field("name", name, include_deleted=include_deleted)

    async def sync_declared(self, declared: Mapping[str, str]) -> set[str]:
        """Make the table hold every ``declared`` permission (name ->
        description): insert the missing ones, refresh changed descriptions and
        restore soft-deleted ones. Returns the names it inserted. Rows no longer
        declared are left alone - roles may still hold them."""
        existing = set((await self.db.execute(select(Permission.name))).scalars().all())
        now = datetime.now(UTC)
        stmt = pg_insert(Permission).values(
            [
                {
                    "name": name,
                    "description": description,
                    "created_at": now,
                    "updated_at": now,
                }
                for name, description in declared.items()
            ],
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Permission.name],
            set_={
                "description": stmt.excluded.description,
                "deleted_at": None,
                "updated_at": now,
            },
            where=Permission.description.is_distinct_from(stmt.excluded.description)
            | Permission.deleted_at.is_not(None),
        )
        await self.db.execute(stmt)
        return set(declared) - existing

    async def get_undeclared_names(self, declared: Mapping[str, str]) -> list[str]:
        """Live permissions no installed module declares any more."""
        rs = await self.db.execute(
            select(Permission.name)
            .where(
                Permission.name.not_in(list(declared)),
                Permission.deleted_at.is_(None),
            )
            .order_by(Permission.name),
        )
        return list(rs.scalars().all())
