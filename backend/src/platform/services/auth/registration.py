import logging
from collections.abc import Callable
from datetime import UTC, datetime

from src.platform.core.config import settings
from src.platform.core.exceptions import (
    AlreadyExistsException,
    NotAuthenticatedException,
)
from src.platform.core.hooks import HookEvent, emit
from src.platform.core.security import (
    Token,
    hash_secret,
    sign,
    unsign,
    verify_secret,
)
from src.platform.enums import (
    AuditAction,
    ErrorCode,
)
from src.platform.schemas.user import (
    CompleteRegistrationIn,
    RegisterIn,
    RegisterOut,
    SetupTokenOut,
    VerifyEmailIn,
)
from src.platform.services.auth.base import _MFA_RESET, AuthBaseService
from src.platform.services.email_content import normalize_locale
from src.platform.services.mailer import send_email
from src.platform.services.organization import setup_new_organization

log = logging.getLogger(__name__)


class RegistrationService(AuthBaseService):
    """Sign-up: register an email, verify it, and create the account and its
    organization."""

    async def register_organization(
        self,
        register_in: RegisterIn,
        schedule_task: Callable,
    ) -> RegisterOut:
        if await self.repos.user.get_by_email(register_in.email):
            raise AlreadyExistsException(
                f"Account already exists. [email={register_in.email}]",
                error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
            )

        terms_accepted_at = datetime.now(UTC)
        token = sign(
            data={"email": register_in.email, "locale": register_in.locale},
            salt="email-verification",
        )
        await self.repos.email_verification_token.delete_by_email(register_in.email)
        await self.repos.email_verification_token.create(
            email=register_in.email,
            token=hash_secret(token),
            terms_accepted_at=terms_accepted_at,
        )
        schedule_task(
            send_email,
            address=register_in.email,
            user_name=register_in.email,
            email_template="verify-email",
            locale=register_in.locale,
            data={
                "verify_url": (f"{settings.frontend_url}/verify-email?token={token}"),
                "expiration_hours": settings.email_verification_expiry // 3600,
            },
        )
        return RegisterOut(message="Check your email to verify your account.")

    async def verify_email(self, schema_in: VerifyEmailIn) -> SetupTokenOut:
        payload: dict | str = unsign(
            schema_in.token,
            salt="email-verification",
            max_age=settings.email_verification_expiry,
        )
        # Support both the legacy plain-string payload and the current dict payload.
        if isinstance(payload, dict):
            email: str = payload["email"]
            locale: str = normalize_locale(payload.get("locale"))
        else:
            email = payload
            locale = "da"

        record = await self.repos.email_verification_token.get_by_email(email)
        if not record or not verify_secret(schema_in.token, record.token):
            raise NotAuthenticatedException(
                "Token invalid",
                error_code=ErrorCode.TOKEN_INVALID,
            )

        terms_accepted_at = record.terms_accepted_at
        await self.repos.email_verification_token.delete_by_email(email)

        setup_token = sign(
            data={
                "email": email,
                "locale": locale,
                "terms_accepted_at": (
                    terms_accepted_at.isoformat() if terms_accepted_at else None
                ),
            },
            salt="complete-registration",
        )
        return SetupTokenOut(setup_token=setup_token)

    async def complete_registration(
        self,
        schema_in: CompleteRegistrationIn,
        schedule_task: Callable,
    ) -> Token:
        payload: dict = unsign(
            schema_in.setup_token,
            salt="complete-registration",
            max_age=settings.complete_registration_expiry,
        )
        email: str = payload["email"]
        locale: str = normalize_locale(payload.get("locale"))
        raw_ts: str | None = payload.get("terms_accepted_at")
        terms_accepted_at = (
            datetime.fromisoformat(raw_ts) if raw_ts else datetime.now(UTC)
        )

        if await self.repos.user.get_by_email(email):
            raise AlreadyExistsException(
                f"Account already exists. [email={email}]",
                error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
            )

        hashed_pw = hash_secret(schema_in.password)

        # Restore soft-deleted user (orphaned when their org was deleted) rather than
        # creating a duplicate row that would violate the email unique constraint.
        deleted_user = await self.repos.user.get_by_email(email, include_deleted=True)
        if deleted_user:
            user = await self.repos.user.restore(deleted_user)
            user = await self.repos.user.update(
                user,
                name=schema_in.name,
                password=hashed_pw,
                terms_accepted_at=terms_accepted_at,
                locale=locale,
                **_MFA_RESET,
            )
        else:
            user = await self.repos.user.create(
                name=schema_in.name,
                email=email,
                password=hashed_pw,
                terms_accepted_at=terms_accepted_at,
                locale=locale,
            )

        organization = await self.repos.organization.create(
            name=f"{schema_in.name}'s Organisation",
        )
        await self.repos.user_organization.create(
            user_id=user.id,
            organization_id=organization.id,
            last_active_at=datetime.now(UTC),
        )
        await emit(
            HookEvent.MEMBER_ADDED,
            repos=self.repos,
            organization_id=organization.id,
            user_id=user.id,
        )

        await setup_new_organization(self.repos, organization, user)

        # Re-fetch user so roles assigned by setup_new_organization are loaded
        user = await self.repos.user.unscoped.get_one(user.id)

        await self.log_audit(
            AuditAction.AUTH_REGISTER,
            organization_id=organization.id,
            user_id=user.id,
        )
        await self.log_audit(
            AuditAction.USER_CONSENT,
            organization_id=organization.id,
            user_id=user.id,
            details={"terms_accepted_at": terms_accepted_at.isoformat()},
        )

        schedule_task(
            send_email,
            address=email,
            user_name=schema_in.name,
            email_template="welcome",
            locale=user.locale,
            data={"login_url": f"{settings.frontend_url}/login"},
        )

        return await self._issue_tokens(user, organization.id)
