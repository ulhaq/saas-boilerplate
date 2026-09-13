import hashlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.core.composition import ALL_PERMISSIONS
from src.platform.core.config import settings
from src.platform.core.context import auth_context_var
from src.platform.core.database import get_db
from src.platform.core.exceptions import (
    NotAuthenticatedException,
    PermissionDeniedException,
    PlanFeatureUnavailableException,
)
from src.platform.core.security import BEARER_HEADERS, Auth, decode_token, oauth2_scheme
from src.platform.enums import OWNER_ROLE_NAME, ErrorCode, PlanFeature
from src.platform.repositories.api_token import ApiTokenRepository
from src.platform.repositories.billing import PlanFeatureRepository
from src.platform.repositories.repository_manager import RepositoryManager
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

    features = await PlanFeatureRepository(db).get_features_for_organization(
        api_token.organization_id
    )
    if PlanFeature.API_TOKEN not in features:
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
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> Auth:
    if not settings.auth_enabled:
        # Local-only shim (config forbids auth_enabled=False in production).
        return Auth(
            id=0,
            name="",
            email="",
            organization_id=0,
            permissions=[p.value for p in ALL_PERMISSIONS],
            roles=[],
        )

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
        repos: Annotated[RepositoryManager, Depends()],
    ) -> Auth:
        if not settings.auth_enabled:
            return current_user
        features = await repos.plan_feature.get_features_for_organization(
            current_user.organization_id
        )
        if feature not in features:
            raise PlanFeatureUnavailableException
        return current_user

    return _check


def require_owner() -> Callable:
    async def _check(
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> Auth:
        if not settings.auth_enabled or OWNER_ROLE_NAME in current_user.roles:
            return current_user
        raise PermissionDeniedException

    return _check
