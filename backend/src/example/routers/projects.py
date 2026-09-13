from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.example.enums import ExamplePermission
from src.example.schemas.project import ProjectIn, ProjectOut, ProjectPatch
from src.example.services.project import ProjectService
from src.platform.core.dependencies import require_permission
from src.platform.core.security import Auth
from src.platform.routers.query_options import (
    PageNumberQuery,
    PageSizeQuery,
    SearchQuery,
    filters_query,
    sort_query,
)
from src.platform.schemas.common import FilterItem, PageQueryParams, PaginatedResponse

router = APIRouter(prefix="/projects")


@router.get("", status_code=status.HTTP_200_OK)
async def list_projects(
    *,
    service: Annotated[ProjectService, Depends()],
    _: Annotated[Auth, Depends(require_permission(ExamplePermission.READ_PROJECT))],
    sort: Annotated[list[str], Depends(sort_query(["description"]))],
    filters: Annotated[list[FilterItem], Depends(filters_query(["description"]))],
    q: SearchQuery,
    page_size: PageSizeQuery = 20,
    page_number: PageNumberQuery = 1,
) -> PaginatedResponse[ProjectOut]:
    return await service.paginate(
        ProjectOut,
        PageQueryParams(
            sort=sort,
            filters=filters,
            page_size=page_size,
            page_number=page_number,
            search=q,
        ),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_a_project(
    service: Annotated[ProjectService, Depends()],
    _: Annotated[Auth, Depends(require_permission(ExamplePermission.CREATE_PROJECT))],
    project_in: ProjectIn,
) -> ProjectOut:
    return await service.create_project(project_in)


@router.get("/{project_id}", status_code=status.HTTP_200_OK)
async def get_a_project(
    service: Annotated[ProjectService, Depends()],
    _: Annotated[Auth, Depends(require_permission(ExamplePermission.READ_PROJECT))],
    project_id: Annotated[int, Path()],
) -> ProjectOut:
    return ProjectOut.model_validate(await service.get(project_id))


@router.patch("/{project_id}", status_code=status.HTTP_200_OK)
async def patch_a_project(
    service: Annotated[ProjectService, Depends()],
    _: Annotated[Auth, Depends(require_permission(ExamplePermission.UPDATE_PROJECT))],
    project_id: Annotated[int, Path()],
    project_in: ProjectPatch,
) -> ProjectOut:
    return await service.patch_project(project_id, project_in)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_a_project(
    service: Annotated[ProjectService, Depends()],
    _: Annotated[Auth, Depends(require_permission(ExamplePermission.DELETE_PROJECT))],
    project_id: Annotated[int, Path()],
) -> None:
    await service.delete_project(project_id)
