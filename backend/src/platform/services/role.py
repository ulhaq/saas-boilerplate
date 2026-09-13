from typing import Annotated

from fastapi import Depends

from src.platform.core.dependencies import authenticate
from src.platform.core.exceptions import (
    AlreadyExistsException,
    PermissionDeniedException,
)
from src.platform.core.security import Auth
from src.platform.enums import AuditAction, ErrorCode
from src.platform.models.role import Role
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.repositories.role import RoleRepository
from src.platform.schemas.common import PageQueryParams, PaginatedResponse
from src.platform.schemas.role import RoleIn, RoleOut, RolePatch, RolePermissionIn
from src.platform.services.base import ResourceService


class RoleService(ResourceService[RoleRepository, Role, RoleIn | RolePatch, RoleOut]):
    current_user: Auth

    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        self.repo = repos.role
        self.repo.set_organization_scope(current_user.organization_id)
        self.current_user = current_user
        super().__init__(repos)

    async def _assert_not_protected_role(self, identifier: int) -> Role:
        role = await self.get(identifier)
        if role.is_protected:
            raise PermissionDeniedException(
                "Protected roles cannot be modified or deleted",
                error_code=ErrorCode.PROTECTED_ROLE_MODIFICATION,
            )
        return role

    async def paginate(
        self,
        schema_out: type[RoleOut],
        page_query_params: PageQueryParams,
        include_deleted: bool = False,
    ) -> PaginatedResponse[RoleOut]:
        return await super().paginate(
            schema_out=schema_out,
            page_query_params=page_query_params,
            include_deleted=include_deleted,
        )

    async def create_role(self, schema_in: RoleIn) -> RoleOut:
        async def validate() -> None:
            if await self.repo.get_by_name(schema_in.name):
                raise AlreadyExistsException(
                    f"Role already exists. [name={schema_in.name}]",
                    error_code=ErrorCode.ROLE_NAME_TAKEN,
                )

        role = await super().create(schema_in, validate)
        await self.log_audit(
            AuditAction.ROLE_CREATE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="role",
            resource_id=role.id,
            details={"name": schema_in.name},
        )
        return RoleOut.model_validate(role)

    async def patch_role(self, identifier: int, schema_in: RolePatch) -> RoleOut:
        await self._assert_not_protected_role(identifier)

        async def validate() -> None:
            if schema_in.name:
                existing_role = await self.repo.get_by_name(schema_in.name)
                if existing_role and existing_role.id != identifier:
                    raise AlreadyExistsException(
                        f"Role already exists. [name={schema_in.name}]"
                    )

        updated = await super().patch(identifier, schema_in, validate)
        await self.log_audit(
            AuditAction.ROLE_UPDATE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="role",
            resource_id=identifier,
        )
        return RoleOut.model_validate(updated)

    async def get_role(self, identifier: int, include_deleted: bool = False) -> RoleOut:
        return RoleOut.model_validate(
            await super().get(identifier, include_deleted=include_deleted)
        )

    async def delete_role(self, identifier: int, force_delete: bool = False) -> None:
        role = await self._assert_not_protected_role(identifier)
        await self.log_audit(
            AuditAction.ROLE_DELETE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="role",
            resource_id=identifier,
            details={"name": role.name},
        )
        await super().delete(identifier, force_delete=force_delete)

    async def manage_permissions(
        self, identifier: int, schema_in: RolePermissionIn
    ) -> RoleOut:
        role = await self._assert_not_protected_role(identifier)

        current_permissions = {permission.id for permission in role.permissions}
        schema_in_permission_ids = set(schema_in.permission_ids)

        if permissions_to_add := schema_in_permission_ids - current_permissions:
            await self.repo.add_permissions(role, *permissions_to_add)

        if permissions_to_remove := current_permissions - schema_in_permission_ids:
            await self.repo.remove_permissions(role, *permissions_to_remove)

        if permissions_to_add or permissions_to_remove:
            await self.log_audit(
                AuditAction.ROLE_PERMISSION_ASSIGN,
                organization_id=self.current_user.organization_id,
                user_id=self.current_user.id,
                resource_type="role",
                resource_id=identifier,
                details={
                    "added": list(permissions_to_add),
                    "removed": list(permissions_to_remove),
                },
            )

        return RoleOut.model_validate(role)
