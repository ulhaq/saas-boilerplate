from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from src.platform.core.config import settings
from src.platform.core.dependencies import authenticate
from src.platform.core.exceptions import (
    AlreadyExistsException,
    NotAuthenticatedException,
    NotFoundException,
    ValidationException,
)
from src.platform.core.mfa import (
    decrypt_secret,
    encrypt_secret,
    generate_recovery_codes,
    generate_secret,
    hash_recovery_code,
    match_recovery_code,
    provisioning_uri,
    verify_totp,
)
from src.platform.core.security import Auth, authenticate_user
from src.platform.enums import AuditAction, ErrorCode
from src.platform.models.user import User
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.mfa import (
    MfaCodeIn,
    MfaDisableIn,
    MfaRecoveryCodesOut,
    MfaSetupOut,
)
from src.platform.services.base import BaseService


class MfaService(BaseService):
    """Self-service TOTP enrollment for the authenticated user."""

    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        if not settings.mfa_enabled:
            raise NotFoundException()
        self.current_user = current_user
        super().__init__(repos)

    async def _get_user(self) -> User:
        user = await self.repos.user.unscoped.get(self.current_user.id)
        if not user:
            raise NotAuthenticatedException()
        return user

    async def _audit(self, action: AuditAction) -> None:
        await self.log_audit(
            action,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="user",
            resource_id=self.current_user.id,
        )

    async def _verify_code(
        self, user: User, code: str, *, allow_recovery: bool
    ) -> None:
        """Accept a fresh TOTP code (or, if allowed, an unused recovery code,
        which is consumed). Raises MFA_CODE_INVALID otherwise."""
        secret = decrypt_secret(user.mfa_secret) if user.mfa_secret else None
        step = verify_totp(secret, code, user.mfa_last_used_step) if secret else None
        if step is not None:
            await self.repos.user.update(user, mfa_last_used_step=step)
            return
        if allow_recovery and (
            used := match_recovery_code(code, user.mfa_recovery_codes)
        ):
            remaining = [h for h in user.mfa_recovery_codes or [] if h != used]
            await self.repos.user.update(user, mfa_recovery_codes=remaining)
            return
        raise ValidationException(
            "Invalid two-factor code", error_code=ErrorCode.MFA_CODE_INVALID
        )

    async def _issue_recovery_codes(self, user: User) -> MfaRecoveryCodesOut:
        codes = generate_recovery_codes()
        await self.repos.user.update(
            user, mfa_recovery_codes=[hash_recovery_code(c) for c in codes]
        )
        return MfaRecoveryCodesOut(recovery_codes=codes)

    async def setup(self) -> MfaSetupOut:
        """Start (or restart) enrollment with a fresh secret. MFA stays off
        until the user confirms a code via enable()."""
        user = await self._get_user()
        if user.mfa_active:
            raise AlreadyExistsException(
                "Two-factor authentication is already enabled",
                error_code=ErrorCode.MFA_ALREADY_ENABLED,
            )
        secret = generate_secret()
        await self.repos.user.update(
            user, mfa_secret=encrypt_secret(secret), mfa_last_used_step=None
        )
        return MfaSetupOut(
            secret=secret, otpauth_uri=provisioning_uri(secret, user.email)
        )

    async def enable(self, schema_in: MfaCodeIn) -> MfaRecoveryCodesOut:
        user = await self._get_user()
        if user.mfa_active:
            raise AlreadyExistsException(
                "Two-factor authentication is already enabled",
                error_code=ErrorCode.MFA_ALREADY_ENABLED,
            )
        if not user.mfa_secret:
            raise ValidationException(
                "Start two-factor setup first", error_code=ErrorCode.MFA_SETUP_REQUIRED
            )
        await self._verify_code(user, schema_in.code, allow_recovery=False)
        await self.repos.user.update(user, mfa_enabled_at=datetime.now(UTC))
        codes = await self._issue_recovery_codes(user)
        await self._audit(AuditAction.USER_MFA_ENABLE)
        return codes

    async def disable(self, schema_in: MfaDisableIn) -> None:
        user = await self._get_user()
        if not user.mfa_active:
            raise ValidationException(
                "Two-factor authentication is not enabled",
                error_code=ErrorCode.MFA_NOT_ENABLED,
            )
        if not authenticate_user(schema_in.password, user):
            raise NotAuthenticatedException(
                "Incorrect password", error_code=ErrorCode.LOGIN_FAILED
            )
        await self._verify_code(user, schema_in.code, allow_recovery=True)
        await self.repos.user.update(
            user,
            mfa_secret=None,
            mfa_enabled_at=None,
            mfa_recovery_codes=None,
            mfa_last_used_step=None,
            mfa_failed_attempts=0,
            mfa_locked_until=None,
        )
        await self._audit(AuditAction.USER_MFA_DISABLE)

    async def regenerate_recovery_codes(
        self, schema_in: MfaCodeIn
    ) -> MfaRecoveryCodesOut:
        user = await self._get_user()
        if not user.mfa_active:
            raise ValidationException(
                "Two-factor authentication is not enabled",
                error_code=ErrorCode.MFA_NOT_ENABLED,
            )
        await self._verify_code(user, schema_in.code, allow_recovery=False)
        codes = await self._issue_recovery_codes(user)
        await self._audit(AuditAction.USER_MFA_RECOVERY_CODES_REGENERATE)
        return codes
