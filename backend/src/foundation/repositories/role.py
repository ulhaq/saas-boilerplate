from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.foundation.models.permission import Permission, RolePermission
from src.foundation.models.role import Role
from src.foundation.repositories.abc import SoftDeleteRepositoryABC
from src.foundation.repositories.base import OrganizationScopedRepository


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
        self,
        name: str,
        *,
        include_deleted: bool = False,
    ) -> Role | None:
        return await self._get_by_field("name", name, include_deleted=include_deleted)

    async def add_permissions(self, role: Role, *permission_ids: int) -> None:
        await self.add_relationship(role, Permission, "permissions", *permission_ids)

    async def remove_permissions(self, role: Role, *permission_ids: int) -> None:
        await self.remove_relationship(role, "permissions", *permission_ids)

    async def grant_to_protected_roles(
        self,
        role_name: str,
        permission_names: Iterable[str],
    ) -> int:
        """Grant every named permission to every organization's protected
        ``role_name`` role (the Owner) that lacks it - across all organizations.
        Returns the number of grants added."""
        now = datetime.now(UTC)
        pairs = (
            select(
                Role.id,
                Permission.id,
                literal(now).label("created_at"),
                literal(now).label("updated_at"),
            )
            .join(Permission, Permission.name.in_(list(permission_names)))
            .where(
                Role.name == role_name,
                Role.is_protected.is_(True),
                Role.deleted_at.is_(None),
                Permission.deleted_at.is_(None),
            )
        )
        stmt = (
            pg_insert(RolePermission)
            .from_select(
                ["role_id", "permission_id", "created_at", "updated_at"],
                pairs,
            )
            .on_conflict_do_nothing(constraint="uq_role_permission")
            .returning(RolePermission.id)
        )
        rs = await self.db.execute(stmt)
        return len(rs.all())
