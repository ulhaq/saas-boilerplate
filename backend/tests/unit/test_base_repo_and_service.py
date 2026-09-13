"""Tests for dead-code paths in repository base and service base."""

import pytest

from src.platform.core.exceptions import PlanFeatureUnavailableException
from src.platform.core.security import Auth
from src.platform.enums import Permission as PermEnum
from src.platform.enums import PlanFeature
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.services.organization import OrganizationService
from tests.conftest import TestSessionLocal

# ---------------------------------------------------------------------------
# SQLResourceRepository.exists()  (base.py:95)
# Exercised via PermissionRepository which extends SQLResourceRepository
# ---------------------------------------------------------------------------


async def test_permission_repo_exists_returns_true():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            # Permission id=1 is always seeded
            assert await repos.permission.exists(1) is True


async def test_permission_repo_exists_returns_false():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            assert await repos.permission.exists(99999) is False


async def test_permission_repo_exists_soft_deleted_excluded_by_default():
    """A soft-deleted permission is not found unless include_deleted=True."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            perm = await repos.permission.create(
                name="exists:test_perm", description="temp"
            )
            perm_id = perm.id
            await repos.permission.delete(perm)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            assert await repos.permission.exists(perm_id) is False
            assert await repos.permission.exists(perm_id, include_deleted=True) is True


# ---------------------------------------------------------------------------
# OrganizationScopedRepository.exists()  (base.py:414)
# Exercised via RoleRepository which extends OrganizationScopedRepository
# ---------------------------------------------------------------------------


async def test_role_repo_exists_returns_true():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.role.set_organization_scope(1)
            # Role id=1 belongs to org 1
            assert await repos.role.exists(1) is True


async def test_role_repo_exists_returns_false_wrong_org():
    """A role that exists but belongs to a different org is not visible."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.role.set_organization_scope(1)
            # Role id=5 belongs to org 2 - invisible from org 1's scope
            assert await repos.role.exists(5) is False


async def test_role_repo_exists_returns_false_missing():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.role.set_organization_scope(1)
            assert await repos.role.exists(99999) is False


# ---------------------------------------------------------------------------
# BaseService._require_feature()  (services/base.py:21-25)
# Exercised via OrganizationService which inherits BaseService
# ---------------------------------------------------------------------------


def _admin_auth() -> Auth:
    return Auth(
        id=1,
        name="Alice",
        email="admin@example.org",
        organization_id=1,
        roles=["Owner"],
        permissions=[p.value for p in PermEnum],
    )


async def test_require_feature_passes_when_feature_available(mock_billing_provider):
    """Org 1 has API_TOKEN on the free plan - should not raise."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = OrganizationService(repos, _admin_auth(), mock_billing_provider)
            # Should complete without raising
            await service._require_feature(PlanFeature.API_TOKEN, organization_id=1)


async def test_require_feature_raises_when_feature_unavailable(mock_billing_provider):
    """An org with no subscription has no features - should raise."""
    from src.platform.models.organization import Organization

    async with TestSessionLocal() as session:
        async with session.begin():
            org = Organization(
                name="No Feature Org", billing_email="billing@example.org"
            )
            session.add(org)
            await session.flush()
            org_id = org.id

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = OrganizationService(repos, _admin_auth(), mock_billing_provider)
            with pytest.raises(PlanFeatureUnavailableException):
                await service._require_feature(
                    PlanFeature.API_TOKEN, organization_id=org_id
                )
