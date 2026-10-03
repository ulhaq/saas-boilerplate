from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.organization import Organization
from src.platform.repositories.base import SoftDeleteRepository


class OrganizationRepository(SoftDeleteRepository[Organization]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Organization, db)

    async def get_by_name(
        self,
        name: str,
        *,
        include_deleted: bool = False,
    ) -> Organization | None:
        return await self._get_by_field("name", name, include_deleted=include_deleted)
