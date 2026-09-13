from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status

from src.platform.core.dependencies import require_permission, require_plan_feature
from src.platform.core.limiter import limiter
from src.platform.core.security import Auth
from src.platform.enums import Permission, PlanFeature
from src.platform.schemas.api_token import (
    ApiTokenCreate,
    ApiTokenCreatedResponse,
    ApiTokenResponse,
)
from src.platform.services.api_token import ApiTokenService

router = APIRouter(prefix="/api-tokens")


@router.get("", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def list_api_tokens(
    request: Request,
    service: Annotated[ApiTokenService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_API_TOKEN))],
    __: Annotated[Auth, Depends(require_plan_feature(PlanFeature.API_TOKEN))],
) -> list[ApiTokenResponse]:
    return await service.list_tokens()


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_api_token(
    request: Request,
    service: Annotated[ApiTokenService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_API_TOKEN))],
    __: Annotated[Auth, Depends(require_plan_feature(PlanFeature.API_TOKEN))],
    token_in: ApiTokenCreate,
) -> ApiTokenCreatedResponse:
    return await service.create_token(token_in)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def revoke_api_token(
    request: Request,
    service: Annotated[ApiTokenService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_API_TOKEN))],
    __: Annotated[Auth, Depends(require_plan_feature(PlanFeature.API_TOKEN))],
    token_id: Annotated[int, Path()],
) -> None:
    await service.revoke_token(token_id)
