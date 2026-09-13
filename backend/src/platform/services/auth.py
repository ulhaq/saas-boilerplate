import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import Depends

from src.platform.billing.dependencies import BillingProviderDep
from src.platform.core.config import settings
from src.platform.core.exceptions import (
    AlreadyExistsException,
    NotAuthenticatedException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from src.platform.core.hooks import HookEvent, emit
from src.platform.core.security import (
    BEARER_HEADERS,
    Auth,
    Token,
    authenticate_user,
    create_token,
    decode_token,
    hash_secret,
    sign,
    unsign,
    verify_secret,
)
from src.platform.enums import (
    OWNER_ROLE_NAME,
    AuditAction,
    ErrorCode,
    RefreshTokenRevokeReason,
)
from src.platform.models.role import Role
from src.platform.models.user import User
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.user import (
    CompleteInviteIn,
    CompleteRegistrationIn,
    EmailIn,
    InviteStatusOut,
    RegisterIn,
    RegisterOut,
    ResetPasswordIn,
    SetupTokenOut,
    VerifyEmailIn,
)
from src.platform.services.base import BaseService
from src.platform.services.email_content import normalize_locale
from src.platform.services.mailer import send_email
from src.platform.services.organization import setup_new_organization

log = logging.getLogger(__name__)


def _filter_assignable_roles(roles: Sequence[Role]) -> list[Role]:
    return [r for r in roles if not (r.is_protected and r.name == OWNER_ROLE_NAME)]


class AuthService(BaseService):
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        provider: BillingProviderDep,
    ) -> None:
        self.provider = provider
        super().__init__(repos)

    async def _issue_tokens(self, user: User, organization_id: int) -> Token:
        """Create an access token plus a new refresh-token session row.

        Each call starts a new session (one row per device/browser); existing
        sessions are untouched. Rotation/revocation is handled by the callers
        via revoke_by_jti / delete_by_user.
        """
        access_token = create_token(
            user, settings.auth_access_token_expiry, organization_id=organization_id
        )
        jti = str(uuid4())
        refresh_token = create_token(
            user,
            settings.auth_refresh_token_expiry,
            include_user_claims=False,
            jti=jti,
            token_type="refresh",
        )
        expires_at = datetime.now(UTC) + timedelta(
            seconds=settings.auth_refresh_token_expiry
        )
        await self.repos.refresh_token.create(
            user, hash_secret(refresh_token), expires_at, jti=jti
        )
        return Token(access_token=access_token, refresh_token=refresh_token)

    async def register_organization(
        self, register_in: RegisterIn, schedule_task: Callable
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
                "Token invalid", error_code=ErrorCode.TOKEN_INVALID
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
        self, schema_in: CompleteRegistrationIn, schedule_task: Callable
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
            billing_email=email,
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

        token = await self._issue_tokens(user, organization.id)

        await self.repos.db.commit()

        return token

    async def invite_status(self, token: str) -> InviteStatusOut:
        data: dict = unsign(token, salt="invite", max_age=settings.invite_expiry)
        email: str = data["email"]

        record = await self.repos.invite_token.get_by_email(email)
        if not record or not verify_secret(token, record.token):
            raise NotAuthenticatedException(
                "Token invalid", error_code=ErrorCode.TOKEN_INVALID
            )

        user_exists = await self.repos.user.get_by_email(email) is not None
        return InviteStatusOut(email=email, user_exists=user_exists)

    async def complete_invite(
        self, schema_in: CompleteInviteIn, schedule_task: Callable
    ) -> Token:
        data: dict = unsign(
            schema_in.invite_token,
            salt="invite",
            max_age=settings.invite_expiry,
        )
        email: str = data["email"]
        organization_id: int = data["organization_id"]
        role_ids: list[int] = data.get("role_ids", [])

        record = await self.repos.invite_token.get_by_email(email)
        if not record or not verify_secret(schema_in.invite_token, record.token):
            raise NotAuthenticatedException(
                "Token invalid", error_code=ErrorCode.TOKEN_INVALID
            )

        await self.repos.invite_token.delete_by_email(email)

        organization = await self.repos.organization.get(organization_id)
        if not organization or organization.deleted_at is not None:
            raise NotFoundException(
                "Organization not found or has been deleted. "
                f"[organization_id={organization_id}]"
            )

        existing_user = await self.repos.user.get_by_email(email)

        if existing_user:
            # Existing user from another org - add them to this org.
            membership = (
                await self.repos.user_organization.get_by_user_and_organization(
                    user_id=existing_user.id,
                    organization_id=organization_id,
                )
            )
            if membership:
                raise AlreadyExistsException(
                    "User is already a member of this organization.",
                    error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
                )

            await self.repos.user_organization.create(
                user_id=existing_user.id,
                organization_id=organization_id,
                last_active_at=datetime.now(UTC),
            )

            if role_ids:
                self.repos.role.set_organization_scope(organization_id)
                valid_roles = _filter_assignable_roles(
                    await self.repos.role.filter_by_ids(role_ids)
                )
                if valid_roles:
                    await self.repos.user.add_roles(
                        existing_user, *[r.id for r in valid_roles]
                    )

            user = await self.repos.user.unscoped.get_one(existing_user.id)

            schedule_task(
                send_email,
                address=email,
                user_name=user.name,
                email_template="added-to-org",
                locale=user.locale,
                data={
                    "organization_name": organization.name,
                    "login_url": f"{settings.frontend_url}/login",
                },
            )
        else:
            # New user - require name and password to create an account.
            if not schema_in.name or not schema_in.password:
                raise ValidationException(
                    "Name and password are required for new accounts."
                )

            invite_now = datetime.now(UTC)
            terms_at = invite_now if schema_in.terms_accepted else None

            # Restore soft-deleted user rather than creating a duplicate that
            # would violate the email unique constraint.
            deleted_user = await self.repos.user.get_by_email(
                email, include_deleted=True
            )
            hashed_pw = hash_secret(schema_in.password)
            if deleted_user:
                user = await self.repos.user.restore(deleted_user)
                user = await self.repos.user.update(
                    user,
                    name=schema_in.name,
                    password=hashed_pw,
                    terms_accepted_at=terms_at,
                )
            else:
                user = await self.repos.user.create(
                    name=schema_in.name,
                    email=email,
                    password=hashed_pw,
                    terms_accepted_at=terms_at,
                )

            if terms_at:
                await self.log_audit(
                    AuditAction.USER_CONSENT,
                    organization_id=organization_id,
                    user_id=user.id,
                    details={"terms_accepted_at": terms_at.isoformat()},
                )

            await self.repos.user_organization.create(
                user_id=user.id,
                organization_id=organization_id,
                last_active_at=datetime.now(UTC),
            )

            if role_ids:
                self.repos.role.set_organization_scope(organization_id)
                valid_roles = _filter_assignable_roles(
                    await self.repos.role.filter_by_ids(role_ids)
                )
                if valid_roles:
                    await self.repos.user.add_roles(user, *[r.id for r in valid_roles])

            user = await self.repos.user.unscoped.get_one(user.id)

        await emit(
            HookEvent.MEMBER_ADDED,
            repos=self.repos,
            organization_id=organization_id,
            user_id=user.id,
        )

        token = await self._issue_tokens(user, organization_id)

        await self.repos.db.commit()

        return token

    async def get_access_token(self, username: str, password: str) -> Token:
        user = authenticate_user(
            password, await self.repos.user.get_by_email(username.lower())
        )

        if not user:
            raise NotAuthenticatedException(
                error_code=ErrorCode.LOGIN_FAILED,
                headers=BEARER_HEADERS,
            )

        membership = (
            await self.repos.user_organization.get_active_organization_for_user(user.id)
        )
        if not membership:
            raise NotAuthenticatedException(
                error_code=ErrorCode.LOGIN_FAILED,
                headers=BEARER_HEADERS,
            )

        await self.repos.user_organization.update_last_active(membership)

        # New session for this device; other sessions stay active. Expired
        # rows for this user are pruned opportunistically.
        await self.repos.refresh_token.delete_expired_for_user(user)
        token = await self._issue_tokens(user, membership.organization_id)

        await self.log_audit(
            AuditAction.AUTH_LOGIN,
            organization_id=membership.organization_id,
            user_id=user.id,
        )

        return token

    async def refresh_access_token(self, refresh_token: str | None) -> Token:
        if not refresh_token:
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        payload = decode_token(refresh_token, expected_type="refresh")
        user_id = int(payload.get("sub", 0))
        jti: str | None = payload.get("jti")

        if not user_id or not jti:
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        user = await self.repos.user.unscoped.get(user_id)
        if not user:
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        stored_token = await self.repos.refresh_token.get_by_jti(jti)
        if not stored_token:
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        if stored_token.user_id != user.id or not verify_secret(
            refresh_token, stored_token.token
        ):
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        if stored_token.revoked_at is not None:
            if stored_token.revoked_reason == RefreshTokenRevokeReason.ROTATED:
                # A rotated token coming back means it was replayed - either
                # by an attacker or by a victim after theft. Revoke every
                # session for this user (OWASP rotation guidance).
                log.warning(
                    "Refresh token reuse detected; revoking all sessions "
                    "[user_id=%s jti=%s]",
                    user_id,
                    jti,
                )
                await self.repos.refresh_token.delete_by_user(user)
                # Commit now: raising 401 rolls back the request transaction,
                # which would otherwise undo the revocation.
                await self.repos.db.commit()
            # Post-logout retries are benign - reject without escalating.
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        membership = (
            await self.repos.user_organization.get_active_organization_for_user(user.id)
        )
        if not membership:
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        # Rotate this session only - other devices keep their sessions.
        await self.repos.refresh_token.revoke_by_jti(
            jti, RefreshTokenRevokeReason.ROTATED
        )

        return await self._issue_tokens(user, membership.organization_id)

    async def switch_organization(
        self,
        current_user: Auth,
        organization_id: int,
        refresh_token: str | None = None,
    ) -> Token:
        user = await self.repos.user.unscoped.get(current_user.id)
        if not user:
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        membership = await self.repos.user_organization.get_by_user_and_organization(
            current_user.id, organization_id
        )
        if not membership:
            raise PermissionDeniedException("You are not a member of this organization")

        await self.repos.user_organization.update_last_active(membership)

        # Rotate this device's session if its refresh cookie was presented;
        # never touch other devices' sessions.
        session_jti = self._decode_session_jti(refresh_token, user_id=user.id)
        if session_jti:
            await self.repos.refresh_token.revoke_by_jti(
                session_jti, RefreshTokenRevokeReason.ROTATED
            )

        return await self._issue_tokens(user, organization_id)

    async def logout(self, refresh_token: str | None) -> None:
        # Ends only this device's session; other sessions stay active.
        session_jti = self._decode_session_jti(refresh_token)
        if session_jti:
            await self.repos.refresh_token.revoke_by_jti(
                session_jti, RefreshTokenRevokeReason.LOGOUT
            )

    def _decode_session_jti(
        self, refresh_token: str | None, user_id: int | None = None
    ) -> str | None:
        """Best-effort extraction of the session jti from a refresh token.
        Returns None for missing/invalid/expired tokens or a user mismatch."""
        if not refresh_token:
            return None
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except Exception:
            return None
        if user_id is not None and int(payload.get("sub", 0)) != user_id:
            return None
        return payload.get("jti")

    async def request_password_reset(
        self, email_in: EmailIn, schedule_task: Callable
    ) -> None:
        user = await self.repos.user.get_by_email(email_in.email)
        if not user:
            log.info("Password reset request failed. [email=%s]", email_in.email)
            return None

        token = sign(data=email_in.email, salt="reset-password")

        await self.repos.user.delete_password_reset_token(user=user)
        await self.repos.user.create_password_reset_token(
            user=user, token=hash_secret(token)
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

        return None

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
                    "Token invalid", error_code=ErrorCode.TOKEN_INVALID
                )

            await self.repos.user.delete_password_reset_token(user=user)
            await self.repos.refresh_token.delete_by_user(user)

            hashed_pw = hash_secret(reset_password_in.password)

            await self.repos.user.update(user, password=hashed_pw)

            await self.log_audit(
                AuditAction.AUTH_PASSWORD_RESET,
                user_id=user.id,
            )

            return None

        raise NotFoundException(f"User not found. [{email=}]")
