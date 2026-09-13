from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, status

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
from src.platform.schemas.user import (
    ChangePasswordIn,
    DeleteMeIn,
    InviteUserIn,
    UserDataExportOut,
    UserOut,
    UserPatch,
    UserRoleIn,
)
from src.platform.services.user import UserService

router = APIRouter(prefix="/users")


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_authenticated_user(service: Annotated[UserService, Depends()]) -> UserOut:
    return await service.get_authenticated_user()


@router.patch("/me", status_code=status.HTTP_200_OK)
async def patch_profile_of_authenticated_user(
    service: Annotated[UserService, Depends()], user_patch: UserPatch
) -> UserOut:
    return await service.patch_profile(user_patch)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    bg_tasks: BackgroundTasks,
    service: Annotated[UserService, Depends()],
    delete_me_in: DeleteMeIn,
) -> None:
    await service.delete_me(delete_me_in, bg_tasks.add_task)


@router.put("/me/change-password", status_code=status.HTTP_200_OK)
async def change_password_of_authenticated_user(
    service: Annotated[UserService, Depends()], change_password_in: ChangePasswordIn
) -> UserOut:
    return await service.change_password(change_password_in)


@router.get("/me/export", status_code=status.HTTP_200_OK)
async def export_my_data(
    service: Annotated[UserService, Depends()],
) -> UserDataExportOut:
    return await service.export_me()


@router.get("", status_code=status.HTTP_200_OK)
async def get_all_users(
    *,
    service: Annotated[UserService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.READ_USER))],
    sort: Annotated[list[str], Depends(sort_query())],
    filters: Annotated[list[FilterItem], Depends(filters_query(["email"]))],
    q: SearchQuery,
    page_size: PageSizeQuery = 10,
    page_number: PageNumberQuery = 1,
) -> PaginatedResponse[UserOut]:
    return await service.paginate(
        UserOut,
        PageQueryParams(
            sort=sort,
            filters=filters,
            page_size=page_size,
            page_number=page_number,
            search=q,
        ),
    )


@router.post("/invite", status_code=status.HTTP_204_NO_CONTENT)
async def invite_a_user(
    bg_tasks: BackgroundTasks,
    service: Annotated[UserService, Depends()],
    _: Annotated[
        Auth, Depends(require_permission(Permission.MANAGE_ORGANIZATION_USER))
    ],
    invite_in: InviteUserIn,
) -> None:
    await service.invite_user(invite_in, bg_tasks.add_task)


@router.patch("/{identifier}", status_code=status.HTTP_200_OK)
async def patch_a_user(
    service: Annotated[UserService, Depends()],
    _: Annotated[
        Auth, Depends(require_permission(Permission.MANAGE_ORGANIZATION_USER))
    ],
    identifier: Annotated[int, Path()],
    user_patch: UserPatch,
) -> UserOut:
    return await service.patch_user(identifier, user_patch)


@router.get("/{identifier}", status_code=status.HTTP_200_OK)
async def get_a_user(
    service: Annotated[UserService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.READ_USER))],
    identifier: Annotated[int, Path()],
) -> UserOut:
    return await service.get_user(identifier)


@router.delete("/{identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_organization(
    service: Annotated[UserService, Depends()],
    _: Annotated[
        Auth, Depends(require_permission(Permission.MANAGE_ORGANIZATION_USER))
    ],
    identifier: Annotated[int, Path()],
) -> None:
    await service.remove_user(identifier)


@router.post("/{identifier}/roles", status_code=status.HTTP_200_OK)
async def manage_roles_of_a_user(
    service: Annotated[UserService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_USER_ROLE))],
    identifier: Annotated[int, Path()],
    role_in: UserRoleIn,
) -> UserOut:
    return await service.manage_roles(identifier, role_in)
