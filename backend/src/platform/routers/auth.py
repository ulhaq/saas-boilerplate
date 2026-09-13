from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from src.platform.core.config import settings
from src.platform.core.dependencies import authenticate
from src.platform.core.limiter import limiter
from src.platform.core.security import Auth, Token
from src.platform.schemas.user import (
    CompleteInviteIn,
    CompleteRegistrationIn,
    EmailIn,
    InviteStatusIn,
    InviteStatusOut,
    RegisterIn,
    RegisterOut,
    ResetPasswordIn,
    SetupTokenOut,
    SwitchOrganizationIn,
    VerifyEmailIn,
)
from src.platform.services.auth import AuthService

router = APIRouter(prefix="/auth")


def _set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        expires=settings.auth_refresh_token_expiry,
        secure=settings.app_env != "local",
        samesite="lax",
        path="/v1/auth",
    )


def _delete_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(
        key="refresh_token",
        secure=settings.app_env != "local",
        samesite="lax",
        path="/v1/auth",
    )


@router.post("/register", status_code=status.HTTP_202_ACCEPTED, include_in_schema=False)
@limiter.limit("5/minute")
async def create_an_account(
    request: Request,
    bg_tasks: BackgroundTasks,
    service: Annotated[AuthService, Depends()],
    register_in: RegisterIn,
) -> RegisterOut:
    return await service.register_organization(register_in, bg_tasks.add_task)


@router.post("/verify-email", status_code=status.HTTP_200_OK, include_in_schema=False)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    service: Annotated[AuthService, Depends()],
    schema_in: VerifyEmailIn,
) -> SetupTokenOut:
    return await service.verify_email(schema_in)


@router.post(
    "/complete-registration",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@limiter.limit("5/minute")
async def complete_registration(
    request: Request,
    response: Response,
    bg_tasks: BackgroundTasks,
    service: Annotated[AuthService, Depends()],
    schema_in: CompleteRegistrationIn,
) -> Token:
    token = await service.complete_registration(schema_in, bg_tasks.add_task)
    _set_refresh_token_cookie(response, token.refresh_token)
    return token


@router.post("/token", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_access_token(
    request: Request,
    response: Response,
    auth_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends()],
) -> Token:
    token = await service.get_access_token(auth_data.username, auth_data.password)
    _set_refresh_token_cookie(response, token.refresh_token)
    return token


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_access_token(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends()],
) -> Token:
    token = await service.refresh_access_token(request.cookies.get("refresh_token"))
    _set_refresh_token_cookie(response, token.refresh_token)
    return token


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends()],
) -> None:
    await service.logout(request.cookies.get("refresh_token"))
    _delete_refresh_token_cookie(response)


@router.post(
    "/reset-password/request",
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    bg_tasks: BackgroundTasks,
    service: Annotated[AuthService, Depends()],
    email_in: EmailIn,
) -> None:
    return await service.request_password_reset(email_in, bg_tasks.add_task)


@router.post(
    "/reset-password", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False
)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    service: Annotated[AuthService, Depends()],
    reset_password_in: ResetPasswordIn,
) -> None:
    await service.reset_password(reset_password_in)


@router.post("/invite-status", status_code=status.HTTP_200_OK, include_in_schema=False)
@limiter.limit("10/minute")
async def get_invite_status(
    request: Request,
    service: Annotated[AuthService, Depends()],
    schema_in: InviteStatusIn,
) -> InviteStatusOut:
    return await service.invite_status(schema_in.token)


@router.post(
    "/complete-invite", status_code=status.HTTP_201_CREATED, include_in_schema=False
)
@limiter.limit("5/minute")
async def complete_invite(
    request: Request,
    response: Response,
    bg_tasks: BackgroundTasks,
    service: Annotated[AuthService, Depends()],
    schema_in: CompleteInviteIn,
) -> Token:
    token = await service.complete_invite(schema_in, bg_tasks.add_task)
    _set_refresh_token_cookie(response, token.refresh_token)
    return token


@router.post("/switch-organization", status_code=status.HTTP_200_OK)
async def switch_organization(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends()],
    current_user: Annotated[Auth, Depends(authenticate)],
    switch_in: SwitchOrganizationIn,
) -> Token:
    token = await service.switch_organization(
        current_user,
        switch_in.organization_id,
        refresh_token=request.cookies.get("refresh_token"),
    )
    _set_refresh_token_cookie(response, token.refresh_token)
    return token
