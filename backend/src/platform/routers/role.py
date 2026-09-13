from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.platform.core.dependencies import require_permission
from src.platform.core.security import Auth
from src.platform.enums import Permission
from src.platform.routers.query_options import (
    PageNumberQuery,
    PageSizeQuery,
    SearchQuery,
    filters_query,
    sort_query,
)
from src.platform.schemas.common import FilterItem, PageQueryParams, PaginatedResponse
from src.platform.schemas.role import RoleIn, RoleOut, RolePatch, RolePermissionIn
from src.platform.services.role import RoleService

router = APIRouter(prefix="/roles")


@router.get("", status_code=status.HTTP_200_OK)
async def get_all_roles(
    *,
    service: Annotated[RoleService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.READ_ROLE))],
    sort: Annotated[list[str], Depends(sort_query(["description"]))],
    filters: Annotated[list[FilterItem], Depends(filters_query(["description"]))],
    q: SearchQuery,
    page_size: PageSizeQuery = 10,
    page_number: PageNumberQuery = 1,
) -> PaginatedResponse[RoleOut]:
    return await service.paginate(
        RoleOut,
        PageQueryParams(
            sort=sort,
            filters=filters,
            page_size=page_size,
            page_number=page_number,
            search=q,
        ),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_a_role(
    service: Annotated[RoleService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.CREATE_ROLE))],
    role_in: RoleIn,
) -> RoleOut:
    return await service.create_role(role_in)


@router.patch("/{identifier}", status_code=status.HTTP_200_OK)
async def patch_a_role(
    service: Annotated[RoleService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.UPDATE_ROLE))],
    identifier: Annotated[int, Path()],
    role_in: RolePatch,
) -> RoleOut:
    return await service.patch_role(identifier, role_in)


@router.get("/{identifier}", status_code=status.HTTP_200_OK)
async def retrieve_a_role(
    service: Annotated[RoleService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.READ_ROLE))],
    identifier: Annotated[int, Path()],
) -> RoleOut:
    return await service.get_role(identifier)


@router.delete("/{identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_role(
    service: Annotated[RoleService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.DELETE_ROLE))],
    identifier: Annotated[int, Path()],
) -> None:
    await service.delete_role(identifier)


@router.post("/{identifier}/permissions", status_code=status.HTTP_200_OK)
async def manage_permissions_of_a_role(
    service: Annotated[RoleService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_ROLE_PERMISSION))],
    identifier: Annotated[int, Path()],
    role_permission_in: RolePermissionIn,
) -> RoleOut:
    return await service.manage_permissions(identifier, role_permission_in)
