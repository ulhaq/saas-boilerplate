import logging
from collections.abc import Callable

from src.foundation.core.config import settings
from src.foundation.core.exceptions import (
    AlreadyExistsException,
    NotAuthenticatedException,
    NotFoundException,
)
from src.foundation.core.security import (
    hash_secret,
    sign,
    unsign,
    verify_secret,
)
from src.foundation.enums import (
    AuditAction,
    ErrorCode,
)
from src.foundation.schemas.user import (
    EmailIn,
    ResetPasswordIn,
)
from src.foundation.services.auth.base import AuthBaseService
from src.foundation.services.mailer import send_email

log = logging.getLogger(__name__)


class CredentialsService(AuthBaseService):
    """Changing credentials from an emailed link: confirming an email change
    and resetting a password."""

    async def confirm_email_change(self, token: str, schedule_task: Callable) -> None:
        """Apply a requested email change from the link sent to the new
        address, then sign the user out everywhere."""
        payload: dict = unsign(
            token,
            salt="email-change",
            max_age=settings.email_change_expiry,
        )
        user = await self.repos.user.unscoped.get(int(payload["uid"]))
        # A changed current email means the link is stale or already used.
        if not user or user.email != payload["old"]:
            raise NotAuthenticatedException(
                "Token invalid",
                error_code=ErrorCode.TOKEN_INVALID,
            )

        old_email: str = payload["old"]
        new_email: str = payload["new"]
        # Re-checked: the address may have been taken since the request.
        if await self.repos.user.get_by_email(new_email, include_deleted=True):
            raise AlreadyExistsException(
                f"Email already in use. [email={new_email}]",
                error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
            )

        await self.repos.user.update(user, email=new_email)
        # The link may be opened on any device, so every session is ended;
        # the user signs in again with the new address.
        await self.repos.refresh_token.delete_by_user(user)

        await self.log_audit(
            AuditAction.USER_EMAIL_CHANGE,
            user_id=user.id,
            resource_type="user",
            resource_id=user.id,
            details={"old_email": old_email, "new_email": new_email},
        )

        schedule_task(
            send_email,
            address=old_email,
            user_name=user.name,
            email_template="email-changed",
            locale=user.locale,
            data={"new_email": new_email},
        )

    async def request_password_reset(
        self,
        email_in: EmailIn,
        schedule_task: Callable,
    ) -> None:
        user = await self.repos.user.get_by_email(email_in.email)
        if not user:
            log.info("Password reset request failed. [email=%s]", email_in.email)
            return

        token = sign(data=email_in.email, salt="reset-password")

        await self.repos.user.delete_password_reset_token(user=user)
        await self.repos.user.create_password_reset_token(
            user=user,
            token=hash_secret(token),
        )

        user_email, user_name, user_locale = user.email, user.name, user.locale

        schedule_task(
            send_email,
            address=user_email,
            user_name=user_name,
            email_template="reset-password",
            locale=user_locale,
            data={
                "reset_url": f"{settings.frontend_url}/reset-password?token={token}",
                "expiration_minutes": settings.auth_password_reset_expiry // 60,
            },
        )

        return

    async def reset_password(self, reset_password_in: ResetPasswordIn) -> None:
        email = unsign(
            token=reset_password_in.token,
            salt="reset-password",
            max_age=settings.auth_password_reset_expiry,
        )
        if user := await self.repos.user.get_by_email(email):
            token = await self.repos.user.get_password_reset_token(user)

            if not token or not verify_secret(reset_password_in.token, token.token):
                raise NotAuthenticatedException(
                    "Token invalid",
                    error_code=ErrorCode.TOKEN_INVALID,
                )

            await self.repos.user.delete_password_reset_token(user=user)
            await self.repos.refresh_token.delete_by_user(user)

            hashed_pw = hash_secret(reset_password_in.password)

            await self.repos.user.update(user, password=hashed_pw)

            await self.log_audit(
                AuditAction.AUTH_PASSWORD_RESET,
                user_id=user.id,
            )

            return

        raise NotFoundException(f"User not found. [{email=}]")
