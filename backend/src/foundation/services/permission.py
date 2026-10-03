from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.foundation.core.exceptions import AlreadyExistsException
from src.foundation.enums import OWNER_ROLE_NAME
from src.foundation.models.permission import Permission
from src.foundation.repositories.permission import PermissionRepository
from src.foundation.repositories.repository_manager import RepositoryManager
from src.foundation.schemas.common import PageQueryParams, PaginatedResponse
from src.foundation.schemas.permission import (
    PermissionIn,
    PermissionOut,
    PermissionPatch,
)
from src.foundation.services.base import ResourceService


class PermissionService(
    ResourceService[
        PermissionRepository,
        Permission,
        PermissionIn | PermissionPatch,
        PermissionOut,
    ],
):
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
    ):
        self.repo = repos.permission
        super().__init__(repos)

    async def paginate(
        self,
        schema_out: type[PermissionOut],
        page_query_params: PageQueryParams,
        *,
        include_deleted: bool = False,
    ) -> PaginatedResponse[PermissionOut]:
        return await super().paginate(
            schema_out=schema_out,
            page_query_params=page_query_params,
            include_deleted=include_deleted,
        )

    async def create_permission(self, schema_in: PermissionIn) -> PermissionOut:
        async def validate() -> None:
            if await self.repo.get_by_name(schema_in.name):
                raise AlreadyExistsException(
                    f"Permission already exists. [name={schema_in.name}]",
                )

        return PermissionOut.model_validate(await super().create(schema_in, validate))

    async def update_permission(
        self,
        identifier: int,
        schema_in: PermissionIn,
    ) -> PermissionOut:
        async def validate() -> None:
            existing_permission = await self.repo.get_by_name(schema_in.name)

            if existing_permission and existing_permission.id != identifier:
                raise AlreadyExistsException(
                    f"Permission already exists. [name={schema_in.name}]",
                )

        return PermissionOut.model_validate(
            await super().update(identifier, schema_in, validate),
        )

    async def patch_permission(
        self,
        identifier: int,
        schema_in: PermissionPatch,
    ) -> PermissionOut:
        async def validate() -> None:
            if schema_in.name:
                existing_permission = await self.repo.get_by_name(schema_in.name)
                if existing_permission and existing_permission.id != identifier:
                    raise AlreadyExistsException(
                        f"Permission already exists. [name={schema_in.name}]",
                    )

        return PermissionOut.model_validate(
            await super().patch(identifier, schema_in, validate),
        )

    async def get_permission(
        self,
        identifier: int,
        *,
        include_deleted: bool = False,
    ) -> PermissionOut:
        return PermissionOut.model_validate(
            await super().get(identifier, include_deleted=include_deleted),
        )

    async def delete_permission(
        self,
        identifier: int,
        *,
        force_delete: bool = False,
    ) -> None:
        await super().delete(identifier, force_delete=force_delete)


@dataclass(frozen=True)
class PermissionSync:
    added: set[str]
    granted: int
    undeclared: list[str]


async def sync_permissions(
    repos: RepositoryManager,
    declared: Mapping[str, str],
) -> PermissionSync:
    """Bring the database in line with the permissions the installed modules
    declare (name -> description): add the missing ones and grant every
    declared permission to every Owner role. Idempotent; run after migrations
    on each deploy (`python -m src.sync_permissions`).

    Other roles are never changed - owners manage them. Permissions no longer
    declared are reported, not removed: roles may still hold them."""
    added = await repos.permission.sync_declared(declared)
    granted = await repos.role.unscoped.grant_to_protected_roles(
        OWNER_ROLE_NAME,
        declared,
    )
    undeclared = await repos.permission.get_undeclared_names(declared)
    return PermissionSync(added=added, granted=granted, undeclared=undeclared)
