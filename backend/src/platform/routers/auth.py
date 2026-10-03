from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from src.platform.core.config import settings
from src.platform.core.limiter import limiter
from src.platform.core.security import Auth, Token
from src.platform.schemas.mfa import MfaChallengeOut, MfaVerifyIn
from src.platform.schemas.user import (
    AcceptInviteIn,
    CompleteInviteIn,
    CompleteRegistrationIn,
    ConfirmEmailChangeIn,
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
from src.platform.services.access import authenticate, authenticate_user_session
from src.platform.services.auth import (
    CredentialsService,
    InviteService,
    RegistrationService,
    SessionService,
)

router = APIRouter(prefix="/auth")
# Sign-up, invite and password flows driven by the app's own pages - mounted
# outside the public API schema (see ROUTERS in src/main.py).
internal_router = APIRouter(prefix="/auth")


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


@internal_router.post("/register", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
async def create_an_account(
    request: Request,  # noqa: ARG001
    bg_tasks: BackgroundTasks,
    service: Annotated[RegistrationService, Depends()],
    register_in: RegisterIn,
) -> RegisterOut:
    return await service.register_organization(register_in, bg_tasks.add_task)


@internal_router.post("/verify-email", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,  # noqa: ARG001
    service: Annotated[RegistrationService, Depends()],
    schema_in: VerifyEmailIn,
) -> SetupTokenOut:
    return await service.verify_email(schema_in)


@internal_router.post(
    "/complete-registration",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def complete_registration(
    request: Request,  # noqa: ARG001
    response: Response,
    bg_tasks: BackgroundTasks,
    service: Annotated[RegistrationService, Depends()],
    schema_in: CompleteRegistrationIn,
) -> Token:
    token = await service.complete_registration(schema_in, bg_tasks.add_task)
    _set_refresh_token_cookie(response, token.refresh_token)
    return token


@router.post("/token", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_access_token(
    request: Request,  # noqa: ARG001
    response: Response,
    auth_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[SessionService, Depends()],
) -> Token | MfaChallengeOut:
    """Returns a Token, or - when the user has two-factor auth enabled - an
    MfaChallengeOut to exchange at POST /auth/mfa/verify."""
    token = await service.get_access_token(auth_data.username, auth_data.password)
    if isinstance(token, Token):
        _set_refresh_token_cookie(response, token.refresh_token)
    return token


@router.post("/mfa/verify", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def verify_mfa(
    request: Request,  # noqa: ARG001
    response: Response,
    service: Annotated[SessionService, Depends()],
    schema_in: MfaVerifyIn,
) -> Token:
    token = await service.verify_mfa(schema_in)
    _set_refresh_token_cookie(response, token.refresh_token)
    return token


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_access_token(
    request: Request,
    response: Response,
    service: Annotated[SessionService, Depends()],
) -> Token:
    token = await service.refresh_access_token(request.cookies.get("refresh_token"))
    _set_refresh_token_cookie(response, token.refresh_token)
    return token


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    service: Annotated[SessionService, Depends()],
) -> None:
    await service.logout(request.cookies.get("refresh_token"))
    _delete_refresh_token_cookie(response)


@internal_router.post(
    "/reset-password/request",
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,  # noqa: ARG001
    bg_tasks: BackgroundTasks,
    service: Annotated[CredentialsService, Depends()],
    email_in: EmailIn,
) -> None:
    return await service.request_password_reset(email_in, bg_tasks.add_task)


@internal_router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,  # noqa: ARG001
    service: Annotated[CredentialsService, Depends()],
    reset_password_in: ResetPasswordIn,
) -> None:
    await service.reset_password(reset_password_in)


@internal_router.post("/invite-status", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_invite_status(
    request: Request,  # noqa: ARG001
    service: Annotated[InviteService, Depends()],
    schema_in: InviteStatusIn,
) -> InviteStatusOut:
    return await service.invite_status(schema_in.token)


@internal_router.post("/complete-invite", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def complete_invite(
    request: Request,  # noqa: ARG001
    response: Response,
    service: Annotated[InviteService, Depends()],
    schema_in: CompleteInviteIn,
) -> Token:
    """Accept an invite by creating a new account. Existing accounts get
    `invite_login_required` and must use POST /auth/accept-invite."""
    token = await service.complete_invite(schema_in)
    _set_refresh_token_cookie(response, token.refresh_token)
    return token


@internal_router.post("/accept-invite", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def accept_invite(
    request: Request,
    response: Response,
    bg_tasks: BackgroundTasks,
    service: Annotated[InviteService, Depends()],
    current_user: Annotated[Auth, Depends(authenticate_user_session)],
    schema_in: AcceptInviteIn,
) -> Token:
    """Accept an invite as the signed-in user; switches the session to the
    new organization."""
    token = await service.accept_invite(
        current_user,
        schema_in.invite_token,
        bg_tasks.add_task,
        refresh_token=request.cookies.get("refresh_token"),
    )
    _set_refresh_token_cookie(response, token.refresh_token)
    return token


@internal_router.post(
    "/confirm-email-change",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("10/minute")
async def confirm_email_change(
    request: Request,  # noqa: ARG001
    response: Response,
    bg_tasks: BackgroundTasks,
    service: Annotated[CredentialsService, Depends()],
    schema_in: ConfirmEmailChangeIn,
) -> None:
    """Apply an email change from the confirmation link; ends all sessions."""
    await service.confirm_email_change(schema_in.token, bg_tasks.add_task)
    _delete_refresh_token_cookie(response)


@router.post("/switch-organization", status_code=status.HTTP_200_OK)
async def switch_organization(
    request: Request,
    response: Response,
    service: Annotated[SessionService, Depends()],
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
