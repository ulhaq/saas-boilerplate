import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from src.foundation.core.config import settings
from src.foundation.core.exceptions import (
    AlreadyExistsException,
    NotAuthenticatedException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from src.foundation.core.hooks import HookEvent, emit
from src.foundation.core.security import (
    BEARER_HEADERS,
    Auth,
    Token,
    hash_secret,
)
from src.foundation.enums import (
    OWNER_ROLE_NAME,
    AuditAction,
    ErrorCode,
    RefreshTokenRevokeReason,
    UsageMetric,
)
from src.foundation.models.invitation import Invitation
from src.foundation.models.organization import Organization
from src.foundation.models.role import Role
from src.foundation.models.user import User
from src.foundation.schemas.user import (
    CompleteInviteIn,
    InviteStatusOut,
)
from src.foundation.services.auth.base import _MFA_RESET, AuthBaseService
from src.foundation.services.mailer import send_email

log = logging.getLogger(__name__)


def _filter_assignable_roles(roles: Sequence[Role]) -> list[Role]:
    return [r for r in roles if not (r.is_protected and r.name == OWNER_ROLE_NAME)]


class InviteService(AuthBaseService):
    """Joining an organization from an invitation, as a new or an existing account."""

    async def invite_status(self, token: str) -> InviteStatusOut:
        invitation = await self._load_invitation(token)
        user_exists = await self.repos.user.get_by_email(invitation.email) is not None
        return InviteStatusOut(email=invitation.email, user_exists=user_exists)

    async def _load_invitation(self, invite_token: str) -> Invitation:
        """Return the pending invitation for a link token. Does not consume it."""
        invitation = await self.repos.invitation.get_by_token(invite_token)
        if not invitation:
            # Unknown, already accepted, or replaced by a newer invite.
            raise NotAuthenticatedException(
                "Invitation invalid",
                error_code=ErrorCode.INVITE_INVALID,
            )
        if invitation.expires_at <= datetime.now(UTC):
            raise NotAuthenticatedException(
                "Invitation expired",
                error_code=ErrorCode.INVITE_EXPIRED,
            )
        return invitation

    async def _get_live_organization(self, organization_id: int) -> Organization:
        organization = await self.repos.organization.get(organization_id)
        if not organization or organization.deleted_at is not None:
            raise NotFoundException(
                "Organization not found or has been deleted. "
                f"[organization_id={organization_id}]",
            )
        return organization

    async def _add_to_organization(
        self,
        user: User,
        organization_id: int,
        role_ids: list[int],
    ) -> User:
        """Create the membership, grant the invited roles, emit MEMBER_ADDED.
        Returns the user re-fetched with the new roles loaded.

        Checks the seat limit again: it may have dropped (a plan change) since
        the invite was sent. A full organization refuses the join, and the
        rollback leaves the invitation usable once a seat frees up."""
        await self._require_capacity(
            UsageMetric.SEATS,
            organization_id,
            lambda: self.repos.user.count_for_org(organization_id),
        )
        await self.repos.user_organization.create(
            user_id=user.id,
            organization_id=organization_id,
            last_active_at=datetime.now(UTC),
        )
        if role_ids:
            self.repos.role.set_organization_scope(organization_id)
            valid_roles = _filter_assignable_roles(
                await self.repos.role.filter_by_ids(role_ids),
            )
            if valid_roles:
                await self.repos.user.add_roles(user, *[r.id for r in valid_roles])

        await emit(
            HookEvent.MEMBER_ADDED,
            repos=self.repos,
            organization_id=organization_id,
            user_id=user.id,
        )
        return await self.repos.user.unscoped.get_one(user.id)

    async def complete_invite(self, schema_in: CompleteInviteIn) -> Token:
        """Accept an invite by creating a new account (unauthenticated).

        Existing accounts must sign in (password + 2FA) and use
        accept_invite() instead - the invite link only proves control of the
        mailbox, which is not enough to act on an existing account.
        """
        invitation = await self._load_invitation(schema_in.invite_token)
        email = invitation.email
        organization_id = invitation.organization_id
        role_ids = invitation.role_ids

        if await self.repos.user.get_by_email(email):
            raise PermissionDeniedException(
                "Sign in to accept this invitation.",
                error_code=ErrorCode.INVITE_LOGIN_REQUIRED,
            )

        await self.repos.invitation.delete(invitation)
        await self._get_live_organization(organization_id)

        if not schema_in.name or not schema_in.password:
            raise ValidationException(
                "Name and password are required for new accounts.",
            )

        invite_now = datetime.now(UTC)
        terms_at = invite_now if schema_in.terms_accepted else None

        # Restore soft-deleted user rather than creating a duplicate that
        # would violate the email unique constraint.
        deleted_user = await self.repos.user.get_by_email(email, include_deleted=True)
        hashed_pw = hash_secret(schema_in.password)
        if deleted_user:
            user = await self.repos.user.restore(deleted_user)
            user = await self.repos.user.update(
                user,
                name=schema_in.name,
                password=hashed_pw,
                terms_accepted_at=terms_at,
                **_MFA_RESET,
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

        user = await self._add_to_organization(user, organization_id, role_ids)

        return await self._issue_tokens(user, organization_id)

    async def accept_invite(
        self,
        current_user: Auth,
        invite_token: str,
        schedule_task: Callable,
        refresh_token: str | None = None,
    ) -> Token:
        """Accept an invite as the signed-in user and switch the session to
        the new organization."""
        user = await self.repos.user.unscoped.get(current_user.id)
        if not user:
            raise NotAuthenticatedException(headers=BEARER_HEADERS)

        invitation = await self._load_invitation(invite_token)
        organization_id = invitation.organization_id
        role_ids = invitation.role_ids

        # Checked before consuming, so a wrong-account attempt leaves the
        # invite usable by its real recipient.
        if invitation.email.lower() != user.email.lower():
            raise PermissionDeniedException(
                "This invitation was sent to a different email address.",
                error_code=ErrorCode.INVITE_EMAIL_MISMATCH,
            )

        await self.repos.invitation.delete(invitation)
        organization = await self._get_live_organization(organization_id)

        if await self.repos.user_organization.get_by_user_and_organization(
            user_id=user.id,
            organization_id=organization_id,
        ):
            raise AlreadyExistsException(
                "User is already a member of this organization.",
                error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
            )

        user = await self._add_to_organization(user, organization_id, role_ids)

        schedule_task(
            send_email,
            address=user.email,
            user_name=user.name,
            email_template="added-to-org",
            locale=user.locale,
            data={
                "organization_name": organization.name,
                "login_url": f"{settings.frontend_url}/login",
            },
        )

        # Like switch_organization: rotate this device's session only.
        session_jti = self._decode_session_jti(refresh_token, user_id=user.id)
        if session_jti:
            await self.repos.refresh_token.revoke_by_jti(
                session_jti,
                RefreshTokenRevokeReason.ROTATED,
            )

        return await self._issue_tokens(user, organization_id)
