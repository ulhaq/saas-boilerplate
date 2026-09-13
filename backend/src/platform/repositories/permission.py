from abc import ABC
from typing import ClassVar

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
        self, name: str, include_deleted: bool = False
    ) -> Permission | None:
        return await self._get_by_field("name", name, include_deleted)
