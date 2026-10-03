"""Request access control: the FastAPI dependencies that resolve who is
calling and gate what they may do (permissions, plan features, plan limits,
ownership).

Login, registration and token issuing live in `services/auth.py`; this module
only answers "who is this request from, and is it allowed?".
"""

import hashlib
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.core import composition
from src.platform.core.context import auth_context_var
from src.platform.core.database import DbSession
from src.platform.core.exceptions import (
    LimitExceededException,
    NotAuthenticatedException,
    PermissionDeniedException,
    PlanFeatureUnavailableException,
)
from src.platform.core.security import BEARER_HEADERS, Auth, decode_token, oauth2_scheme
from src.platform.enums import OWNER_ROLE_NAME, ErrorCode, PlanFeature
from src.platform.repositories.api_token import ApiTokenRepository
from src.platform.repositories.user import UserRepository
from src.platform.repositories.user_organization import UserOrganizationRepository

TOUCH_LAST_USED_INTERVAL = timedelta(minutes=5)


def _bind_auth_context(auth: Auth) -> None:
    """
    Expose the authenticated identity to the logging context. Mutates the
    holder installed by AuditContextMiddleware in place so the values are
    visible both here (downstream logs) and at the outer access-log layer.
    """
    ctx = auth_context_var.get()
    if ctx is not None:
        ctx["org_id"] = auth.organization_id
        ctx["user_id"] = auth.id


async def _authenticate_api_token(token: str, db: AsyncSession) -> Auth:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    repo = ApiTokenRepository(db)
    api_token = await repo.get_by_hash(token_hash)

    if not api_token:
        raise NotAuthenticatedException(headers=BEARER_HEADERS)

    if api_token.expires_at is not None:
        expires = api_token.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < datetime.now(UTC):
            raise NotAuthenticatedException(
                "Token expired",
                error_code=ErrorCode.TOKEN_EXPIRED,
                headers=BEARER_HEADERS,
            )

    user_repo = UserRepository(db)
    user_repo.set_organization_scope(api_token.organization_id)
    user = await user_repo.get(api_token.user_id)
    if not user:
        raise NotAuthenticatedException(headers=BEARER_HEADERS)

    if not await composition.current().entitlements.has_feature(
        db, api_token.organization_id, PlanFeature.API_TOKEN
    ):
        raise PlanFeatureUnavailableException

    # Throttled: last_used_at is informational, and writing it on every call
    # would add a row update per API request under load.
    last_used = api_token.last_used_at
    if last_used is not None and last_used.tzinfo is None:
        last_used = last_used.replace(tzinfo=UTC)
    if last_used is None or last_used < datetime.now(UTC) - TOUCH_LAST_USED_INTERVAL:
        await repo.touch_last_used(api_token.id, api_token.organization_id)

    auth = Auth.from_user_model(user, api_token.organization_id)
    token_perms = set(api_token.permissions)
    auth.permissions = [p for p in auth.permissions if p in token_perms]
    return auth


async def authenticate(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> Auth:
    if not token:
        raise NotAuthenticatedException(headers=BEARER_HEADERS)

    if token.startswith("sk_"):
        auth = await _authenticate_api_token(token, db)
        _bind_auth_context(auth)
        return auth

    payload = decode_token(token)
    user_id = int(payload.get("sub", 0))
    organization_id = int(payload.get("oid", 0))

    if not organization_id:
        raise NotAuthenticatedException(headers=BEARER_HEADERS)

    # Identity lookup by primary key - intentionally cross-tenant; the org
    # context comes from the signed token, not the query.
    user = await UserRepository(db).unscoped.get(user_id)

    if not user:
        raise NotAuthenticatedException(headers=BEARER_HEADERS)

    # The oid claim is signed, but membership may have been revoked after the
    # token was issued - re-verify it so removal takes effect immediately.
    membership = await UserOrganizationRepository(db).get_by_user_and_organization(
        user_id, organization_id
    )
    if not membership:
        raise NotAuthenticatedException(headers=BEARER_HEADERS)

    auth = Auth.from_user_model(user, organization_id)
    _bind_auth_context(auth)
    return auth


async def authenticate_user_session(
    auth: Annotated[Auth, Depends(authenticate)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> Auth:
    """Like authenticate(), but only for an interactive sign-in (password and,
    if enabled, 2FA) - rejects API tokens. For account-level actions such as
    joining an organization."""
    if token and token.startswith("sk_"):
        raise PermissionDeniedException("This action requires a signed-in user")
    return auth


def assert_can_grant(current_user: Auth, permissions: Iterable[str]) -> None:
    """Refuse to grant or revoke permissions the caller doesn't hold - through a
    role's permissions, a user's roles or an invitation - so nobody can hand out
    more access than they have. Owners hold every permission. (API tokens apply
    the same rule to themselves.)"""
    missing = set(permissions) - set(current_user.permissions)
    if missing:
        raise PermissionDeniedException(
            "You can only grant or revoke permissions you hold yourself."
            f" [missing={','.join(sorted(missing))}]",
            error_code=ErrorCode.PERMISSION_NOT_HELD,
        )


def require_permission(permission: StrEnum) -> Callable:
    async def _check(
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> Auth:
        current_user.authorize(permission)
        return current_user

    return _check


def require_plan_feature(feature: StrEnum) -> Callable:
    async def _check(
        current_user: Annotated[Auth, Depends(authenticate)],
        db: DbSession,
    ) -> Auth:
        if not await composition.current().entitlements.has_feature(
            db, current_user.organization_id, feature
        ):
            raise PlanFeatureUnavailableException
        return current_user

    return _check


def require_owner() -> Callable:
    async def _check(
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> Auth:
        if OWNER_ROLE_NAME in current_user.roles:
            return current_user
        raise PermissionDeniedException

    return _check


def require_limit(metric: StrEnum) -> Callable:
    """
    FastAPI dependency factory that blocks the request with LIMIT_EXCEEDED when
    the organisation has consumed its plan allocation for `metric` this period.
    Use as a default-value dependency on the route parameter list:

        async def my_endpoint(
            _: Annotated[None, Depends(require_limit(UsageMetric.SEATS))],
            ...
        ): ...
    """

    async def _check(
        db: DbSession,
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        entitlements = composition.current().entitlements
        organization_id = current_user.organization_id
        limit = await entitlements.limit(db, organization_id, metric)
        if limit is None:
            return
        if await entitlements.usage(db, organization_id, metric) >= limit:
            raise LimitExceededException()

    return _check


async def track_usage(db: AsyncSession, organization_id: int, metric: StrEnum) -> int:
    """Count one use of a per-period ``metric`` (checked by `require_limit`);
    returns the new count."""
    return await composition.current().entitlements.record_usage(
        db, organization_id, metric
    )
