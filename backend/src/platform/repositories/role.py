from abc import ABC, abstractmethod
from typing import ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.permission import Permission
from src.platform.models.role import Role
from src.platform.repositories.abc import SoftDeleteRepositoryABC
from src.platform.repositories.base import OrganizationScopedRepository


class RoleRepositoryABC(SoftDeleteRepositoryABC[Role], ABC):
    @abstractmethod
    async def add_permissions(self, role: Role, *permission_ids: int) -> None: ...

    @abstractmethod
    async def remove_permissions(self, role: Role, *permission_ids: int) -> None: ...


class RoleRepository(OrganizationScopedRepository[Role], RoleRepositoryABC):
    search_fields: ClassVar[list[str]] = ["name", "description"]

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Role, db)

    async def get_by_name(
        self, name: str, include_deleted: bool = False
    ) -> Role | None:
        return await self._get_by_field("name", name, include_deleted)

    async def add_permissions(self, role: Role, *permission_ids: int) -> None:
        await self.add_relationship(role, Permission, "permissions", *permission_ids)

    async def remove_permissions(self, role: Role, *permission_ids: int) -> None:
        await self.remove_relationship(role, "permissions", *permission_ids)
