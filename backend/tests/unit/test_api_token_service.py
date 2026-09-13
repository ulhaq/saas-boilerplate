"""Direct unit tests for ApiTokenService."""

import pytest

from src.platform.core.exceptions import NotFoundException, ValidationException
from src.platform.core.security import Auth
from src.platform.enums import Permission as PermEnum
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.api_token import ApiTokenCreate
from src.platform.services.api_token import ApiTokenService
from tests.conftest import TestSessionLocal


def _admin_auth(user_id: int = 1, org_id: int = 1) -> Auth:
    return Auth(
        id=user_id,
        name="Alice Owner",
        email="admin@example.org",
        organization_id=org_id,
        roles=["Owner"],
        permissions=[p.value for p in PermEnum],
    )


def _make_service(session, auth: Auth) -> ApiTokenService:
    repos = RepositoryManager(session)
    return ApiTokenService(repos, auth)


# ---------------------------------------------------------------------------
# create_token
# ---------------------------------------------------------------------------


async def test_create_token_success():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth())
            result = await service.create_token(
                ApiTokenCreate(
                    name="My Token",
                    permissions=[PermEnum.MANAGE_USER_ROLE.value],
                )
            )

    assert result.token.startswith("sk_")
    assert result.name == "My Token"


async def test_create_token_invalid_permissions_raises():
    """Requesting permissions the user doesn't have raises ValidationException."""
    no_perm_auth = Auth(
        id=2,
        name="Bob",
        email="standard@example.org",
        organization_id=1,
        roles=["Member"],
        permissions=[],  # no permissions
    )

    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, no_perm_auth)
            with pytest.raises(ValidationException):
                await service.create_token(
                    ApiTokenCreate(
                        name="Bad Token",
                        permissions=[PermEnum.MANAGE_USER_ROLE.value],
                    )
                )


# ---------------------------------------------------------------------------
# list_tokens
# ---------------------------------------------------------------------------


async def test_list_tokens_returns_list():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth())
            result = await service.list_tokens()

    assert isinstance(result, list)


async def test_list_tokens_includes_created_token():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth())
            await service.create_token(
                ApiTokenCreate(
                    name="Listed", permissions=[PermEnum.MANAGE_USER_ROLE.value]
                )
            )
            result = await service.list_tokens()

    assert any(t.name == "Listed" for t in result)


# ---------------------------------------------------------------------------
# revoke_token
# ---------------------------------------------------------------------------


async def test_revoke_token_success():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth())
            created = await service.create_token(
                ApiTokenCreate(
                    name="To Revoke", permissions=[PermEnum.MANAGE_USER_ROLE.value]
                )
            )
            await service.revoke_token(created.id)


async def test_revoke_token_not_found_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth())
            with pytest.raises(NotFoundException):
                await service.revoke_token(99999)
