from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.platform.core.dependencies import require_owner, require_permission
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
from src.platform.schemas.organization import (
    MyOrganizationOut,
    OrganizationBase,
    OrganizationOut,
    OrganizationPatch,
    TransferOwnershipIn,
)
from src.platform.schemas.user import UserOut
from src.platform.services.organization import OrganizationService

router = APIRouter(prefix="/organizations")


@router.get("", status_code=status.HTTP_200_OK)
async def get_all_organizations(
    service: Annotated[OrganizationService, Depends()],
) -> list[MyOrganizationOut]:
    return await service.get_all_organizations()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_an_organization(
    service: Annotated[OrganizationService, Depends()],
    organization_in: OrganizationBase,
) -> OrganizationOut:
    return await service.create_organization(organization_in)


@router.patch("/{identifier}", status_code=status.HTTP_200_OK)
async def patch_an_organization(
    service: Annotated[OrganizationService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.UPDATE_ORGANIZATION))],
    identifier: Annotated[int, Path()],
    organization_in: OrganizationPatch,
) -> OrganizationOut:
    return await service.patch_organization(identifier, organization_in)


@router.get("/{identifier}", status_code=status.HTTP_200_OK)
async def retrieve_an_organization(
    service: Annotated[OrganizationService, Depends()],
    identifier: Annotated[int, Path()],
) -> OrganizationOut:
    return await service.get_organization(identifier)


@router.delete("/{identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_an_organization(
    service: Annotated[OrganizationService, Depends()],
    _: Annotated[Auth, Depends(require_owner())],
    identifier: Annotated[int, Path()],
) -> None:
    await service.delete_organization(identifier)


@router.post(
    "/{organization_id}/transfer-ownership", status_code=status.HTTP_204_NO_CONTENT
)
async def transfer_organization_ownership(
    service: Annotated[OrganizationService, Depends()],
    _: Annotated[Auth, Depends(require_owner())],
    organization_id: Annotated[int, Path()],
    schema_in: TransferOwnershipIn,
) -> None:
    await service.transfer_ownership(organization_id, schema_in)


@router.get("/{organization_id}/users", status_code=status.HTTP_200_OK)
async def get_organization_users(
    *,
    service: Annotated[OrganizationService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.READ_USER))],
    organization_id: Annotated[int, Path()],
    sort: Annotated[list[str], Depends(sort_query())],
    filters: Annotated[list[FilterItem], Depends(filters_query(["email"]))],
    q: SearchQuery,
    page_size: PageSizeQuery = 10,
    page_number: PageNumberQuery = 1,
) -> PaginatedResponse[UserOut]:
    return await service.get_organization_users(
        organization_id,
        PageQueryParams(
            sort=sort,
            filters=filters,
            page_size=page_size,
            page_number=page_number,
            search=q,
        ),
    )
