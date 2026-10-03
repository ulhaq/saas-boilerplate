from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status

from src.foundation.core.cache import set_cache_control
from src.foundation.core.config import settings
from src.foundation.core.security import Auth
from src.foundation.enums import Permission
from src.foundation.routers.query_options import (
    PageNumberQuery,
    PageSizeQuery,
    SearchQuery,
    filters_query,
    sort_query,
)
from src.foundation.schemas.common import FilterItem, PageQueryParams, PaginatedResponse
from src.foundation.schemas.permission import PermissionOut
from src.foundation.services.access import require_permission
from src.foundation.services.permission import PermissionService

router = APIRouter(prefix="/permissions")


@router.get("", status_code=status.HTTP_200_OK)
async def get_all_permissions(
    *,
    response: Response,
    service: Annotated[PermissionService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.READ_PERMISSION))],
    sort: Annotated[list[str], Depends(sort_query(["description"]))],
    filters: Annotated[list[FilterItem], Depends(filters_query(["description"]))],
    q: SearchQuery,
    page_size: PageSizeQuery = 10,
    page_number: PageNumberQuery = 1,
) -> PaginatedResponse[PermissionOut]:
    set_cache_control(response, settings.permissions_cache_max_age)
    return await service.paginate(
        PermissionOut,
        PageQueryParams(
            sort=sort,
            filters=filters,
            page_size=page_size,
            page_number=page_number,
            search=q,
        ),
    )


@router.get("/{identifier}", status_code=status.HTTP_200_OK)
async def retrieve_a_permission(
    response: Response,
    service: Annotated[PermissionService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.READ_PERMISSION))],
    identifier: Annotated[int, Path()],
) -> PermissionOut:
    set_cache_control(response, settings.permissions_cache_max_age)
    return await service.get_permission(identifier)
