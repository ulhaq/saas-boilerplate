"""Service-level plan feature checks against billing's plans."""

from enum import StrEnum

import pytest

from src.platform.core.exceptions import PlanFeatureUnavailableException
from src.platform.core.security import Auth
from src.platform.enums import Permission as PermEnum
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.services.organization import OrganizationService
from tests.conftest import TestSessionLocal


def _admin_auth() -> Auth:
    return Auth(
        id=1,
        name="Alice",
        email="admin@example.org",
        organization_id=1,
        roles=["Owner"],
        permissions=[p.value for p in PermEnum],
    )


async def test_require_feature_raises_when_feature_unavailable():
    """A feature the organization's plan doesn't include - should raise."""

    class _Feature(StrEnum):
        SSO = "sso"

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = OrganizationService(repos, _admin_auth())
            with pytest.raises(PlanFeatureUnavailableException):
                await service._require_feature(_Feature.SSO, organization_id=1)
