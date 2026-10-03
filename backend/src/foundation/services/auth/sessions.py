import logging
from datetime import UTC, datetime, timedelta

from src.foundation.core.config import settings
from src.foundation.core.exceptions import (
    LoginLockedException,
    NotAuthenticatedException,
    NotFoundException,
    PermissionDeniedException,
)
from src.foundation.core.mfa import (
    decrypt_secret,
    match_recovery_code,
    mfa_required,
    verify_totp,
)
from src.foundation.core.security import (
    BEARER_HEADERS,
    Auth,
    Token,
    authenticate_user,
    decode_token,
    sign,
    unsign,
    verify_secret,
)
from src.foundation.enums import (
    AuditAction,
    ErrorCode,
    RefreshTokenRevokeReason,
)
from src.foundation.models.user import User
from src.foundation.models.user_organization import UserOrganization
from src.foundation.schemas.mfa import MfaChallengeOut, MfaVerifyIn
from src.foundation.services.auth.base import AuthBaseService

log = logging.getLogger(__name__)


def _retry_after(until: datetime) -> dict[str, str]:
    seconds = max(1, int((until - datetime.now(UTC)).total_seconds()))
    return {"Retry-After": str(seconds)}


class SessionService(AuthBaseService):
    """Signed-in sessions: password and two-factor sign-in, token refresh,
    switching organization, and logout."""

    async def get_access_token(
        self,
        username: str,
        password: str,
    ) -> Token | MfaChallengeOut:
        email = username.lower()
        # Checked before the password: a locked address is refused the same
        # way whether or not an account exists for it.
        if locked_until := await self.repos.login_throttle.locked_until(email):
            raise LoginLockedException(headers=_retry_after(locked_until))

        user = authenticate_user(password, await self.repos.user.get_by_email(email))

        if not user:
            await self.repos.login_throttle.record_failure(
                email,
                max_attempts=settings.login_max_failed_attempts,
                window=timedelta(seconds=settings.login_lockout_seconds),
            )
            # The failure must count although the request fails.
            await self.repos.commit_before_raise()
            raise NotAuthenticatedException(
                error_code=ErrorCode.LOGIN_FAILED,
                headers=BEARER_HEADERS,
            )
        await self.repos.login_throttle.clear(email)

        membership = (
            await self.repos.user_organization.get_active_organization_for_user(user.id)
        )
        if not membership:
            raise NotAuthenticatedException(
                error_code=ErrorCode.LOGIN_FAILED,
                headers=BEARER_HEADERS,
            )

        if mfa_required(user):
            return self._mfa_challenge(user, membership.organization_id)

        return await self._complete_login(user, membership)

    async def _complete_login(self, user: User, membership: UserOrganization) -> Token:
        organization_id = membership.organization_id
        await self.repos.user_organization.update_last_active(membership)

        # New session for this device; other sessions stay active. Expired
        # rows for this user are pruned opportunistically.
        await self.repos.refresh_token.delete_expired_for_user(user)
        token = await self._issue_tokens(user, organization_id)

        await self.log_audit(
            AuditAction.AUTH_LOGIN,
            organization_id=organization_id,
            user_id=user.id,
        )

        return token

    def _mfa_challenge(self, user: User, organization_id: int) -> MfaChallengeOut:
        mfa_token = sign(
            data={"uid": user.id, "oid": organization_id},
            salt="mfa-challenge",
        )
        return MfaChallengeOut(mfa_token=mfa_token)

    async def verify_mfa(self, schema_in: MfaVerifyIn) -> Token:
        if not settings.mfa_enabled:
            raise NotFoundException

        payload: dict = unsign(
            schema_in.mfa_token,
            salt="mfa-challenge",
            max_age=settings.mfa_challenge_expiry,
        )
        user = await self.repos.user.unscoped.get(int(payload["uid"]))
        if not user or not user.mfa_active or not user.mfa_secret:
            raise NotAuthenticatedException(
                "Token invalid",
                error_code=ErrorCode.TOKEN_INVALID,
            )

        organization_id = int(payload["oid"])
        memberships = await self.repos.user_organization.get_all_for_user(user.id)
        membership = next(
            (m for m in memberships if m.organization_id == organization_id),
            None,
        )
        if not membership:
            raise NotAuthenticatedException(
                error_code=ErrorCode.LOGIN_FAILED,
                headers=BEARER_HEADERS,
            )

        now = datetime.now(UTC)
        if user.mfa_locked_until and user.mfa_locked_until > now:
            raise NotAuthenticatedException(
                "Two-factor verification locked",
                error_code=ErrorCode.MFA_LOCKED,
            )

        secret = decrypt_secret(user.mfa_secret)
        step = (
            verify_totp(secret, schema_in.code, user.mfa_last_used_step)
            if secret
            else None
        )
        if step is not None:
            await self.repos.user.update(user, mfa_last_used_step=step)
        elif used := match_recovery_code(schema_in.code, user.mfa_recovery_codes):
            remaining = [h for h in user.mfa_recovery_codes or [] if h != used]
            await self.repos.user.update(user, mfa_recovery_codes=remaining)
            await self.log_audit(
                AuditAction.AUTH_MFA_RECOVERY_CODE_USED,
                organization_id=organization_id,
                user_id=user.id,
                details={"remaining": len(remaining)},
            )
        else:
            attempts = user.mfa_failed_attempts + 1
            locked = attempts >= settings.mfa_max_failed_attempts
            await self.repos.user.update(
                user,
                mfa_failed_attempts=0 if locked else attempts,
                mfa_locked_until=(
                    now + timedelta(seconds=settings.mfa_lockout_seconds)
                    if locked
                    else None
                ),
            )
            if locked:
                log.warning("MFA verification locked [user_id=%s]", user.id)
            # The attempt count must persist although the request fails.
            await self.repos.commit_before_raise()
            raise NotAuthenticatedException(
                "Invalid two-factor code",
                error_code=ErrorCode.MFA_CODE_INVALID,
            )

        if user.mfa_failed_attempts or user.mfa_locked_until:
            await self.repos.user.update(
                user,
                mfa_failed_attempts=0,
                mfa_locked_until=None,
            )
        return await self._complete_login(user, membership)

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
            refresh_token,
            stored_token.token,
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
                # The revocation must persist although the request fails.
                await self.repos.commit_before_raise()
            # Post-logout retries are benign - reject without escalating.
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        membership = (
            await self.repos.user_organization.get_active_organization_for_user(user.id)
        )
        if not membership:
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        # Rotate this session only - other devices keep their sessions.
        await self.repos.refresh_token.revoke_by_jti(
            jti,
            RefreshTokenRevokeReason.ROTATED,
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
            current_user.id,
            organization_id,
        )
        if not membership:
            raise PermissionDeniedException("You are not a member of this organization")

        await self.repos.user_organization.update_last_active(membership)

        # Rotate this device's session if its refresh cookie was presented;
        # never touch other devices' sessions.
        session_jti = self._decode_session_jti(refresh_token, user_id=user.id)
        if session_jti:
            await self.repos.refresh_token.revoke_by_jti(
                session_jti,
                RefreshTokenRevokeReason.ROTATED,
            )

        return await self._issue_tokens(user, organization_id)

    async def logout(self, refresh_token: str | None) -> None:
        # Ends only this device's session; other sessions stay active.
        session_jti = self._decode_session_jti(refresh_token)
        if session_jti:
            await self.repos.refresh_token.revoke_by_jti(
                session_jti,
                RefreshTokenRevokeReason.LOGOUT,
            )
