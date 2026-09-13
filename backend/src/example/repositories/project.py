from typing import ClassVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.example.models.project import Project
from src.platform.repositories.base import OrganizationScopedRepository


class ProjectRepository(OrganizationScopedRepository[Project]):
    search_fields: ClassVar[list[str]] = ["name", "description"]

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Project, db)

    async def get_by_name(self, name: str) -> Project | None:
        return await self._get_by_field("name", name)

    async def count(self) -> int:
        """Active projects in the current scope (all tenants when `.unscoped`)."""
        stmt = select(func.count()).select_from(Project)
        stmt = self._apply_organization_scope(stmt)
        stmt = self._include_deleted(stmt)
        rs = await self.db.execute(stmt)
        return int(rs.scalar_one())
