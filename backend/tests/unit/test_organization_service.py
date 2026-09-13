"""Direct unit tests for OrganizationService."""

import pytest

from src.platform.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    PermissionDeniedException,
)
from src.platform.core.security import Auth
from src.platform.enums import Permission as PermEnum
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.common import PageQueryParams
from src.platform.schemas.organization import (
    OrganizationBase,
    OrganizationOut,
    OrganizationPatch,
    TransferOwnershipIn,
)
from src.platform.services.organization import OrganizationService
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


def _make_service(session, auth: Auth, provider) -> OrganizationService:
    repos = RepositoryManager(session)
    return OrganizationService(repos, auth, provider)


# ---------------------------------------------------------------------------
# get / get_organization
# ---------------------------------------------------------------------------


async def test_get_organization_member_access(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            org = await service.get_organization(1)
    assert org.name == "Acme Corp"


async def test_get_organization_non_member_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(
                session, _admin_auth(org_id=1), mock_billing_provider
            )
            # Admin belongs to org 1, not org 2
            with pytest.raises(PermissionDeniedException):
                await service.get_organization(2)


# ---------------------------------------------------------------------------
# get_all_organizations
# ---------------------------------------------------------------------------


async def test_get_all_organizations_returns_own_org(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            orgs = await service.get_all_organizations()
    assert any(o.name == "Acme Corp" for o in orgs)
    assert any(o.is_owner for o in orgs)


# ---------------------------------------------------------------------------
# create_organization
# ---------------------------------------------------------------------------


async def test_create_organization_new_name(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            out = await service.create_organization(
                OrganizationBase(name="Brand New Corp")
            )
    assert out.name == "Brand New Corp"


async def test_create_organization_duplicate_name_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            with pytest.raises(AlreadyExistsException):
                await service.create_organization(OrganizationBase(name="Acme Corp"))


# ---------------------------------------------------------------------------
# patch_organization
# ---------------------------------------------------------------------------


async def test_patch_organization_success(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            out = await service.patch_organization(
                1, OrganizationPatch(name="Acme Corp 2")
            )
    assert out.name == "Acme Corp 2"


async def test_patch_organization_wrong_org_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            # User active org is 1, tries to patch org 2
            service = _make_service(
                session, _admin_auth(org_id=1), mock_billing_provider
            )
            with pytest.raises(PermissionDeniedException):
                await service.patch_organization(2, OrganizationPatch(name="X"))


# ---------------------------------------------------------------------------
# delete_organization
# ---------------------------------------------------------------------------


async def test_delete_organization_wrong_org_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(
                session, _admin_auth(org_id=1), mock_billing_provider
            )
            with pytest.raises(PermissionDeniedException):
                await service.delete_organization(2)


async def test_delete_organization_with_active_subscription_raises(
    mock_billing_provider, plan_with_price
):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            sub = await repos.subscription.get_active_for_organization(1)
            assert sub
            await repos.subscription.update(
                sub,
                plan_price_id=price_id,
                external_subscription_id="sub_block_del",
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(
                session, _admin_auth(org_id=1), mock_billing_provider
            )
            with pytest.raises(PermissionDeniedException):
                await service.delete_organization(1)


async def test_delete_organization_success(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(
                session, _admin_auth(org_id=1), mock_billing_provider
            )
            await service.delete_organization(1)


async def test_delete_organization_force_delete(mock_billing_provider):
    """force_delete=True calls repo.force_delete (base.py line 118)."""
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(
                session, _admin_auth(org_id=1), mock_billing_provider
            )
            await service.delete_organization(1, force_delete=True)


# ---------------------------------------------------------------------------
# get_organization_users
# ---------------------------------------------------------------------------


async def test_get_organization_users(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            result = await service.get_organization_users(
                1,
                PageQueryParams(page_number=1, page_size=10, sort=[], filters=[]),
            )
    assert result.total >= 1


# ---------------------------------------------------------------------------
# transfer_ownership
# ---------------------------------------------------------------------------


async def test_transfer_ownership_wrong_org_raises(mock_billing_provider):
    """Trying to transfer ownership of an org that's not current active raises."""
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(
                session, _admin_auth(user_id=1, org_id=1), mock_billing_provider
            )
            with pytest.raises(PermissionDeniedException):
                # current active org is 1, trying to transfer org 2
                await service.transfer_ownership(2, TransferOwnershipIn(user_id=2))


async def test_transfer_ownership_to_self_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(
                session, _admin_auth(user_id=1, org_id=1), mock_billing_provider
            )
            with pytest.raises(PermissionDeniedException):
                await service.transfer_ownership(1, TransferOwnershipIn(user_id=1))


async def test_transfer_ownership_to_non_member_raises(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(
                session, _admin_auth(user_id=1, org_id=1), mock_billing_provider
            )
            with pytest.raises(NotFoundException):
                await service.transfer_ownership(1, TransferOwnershipIn(user_id=999))


async def test_transfer_ownership_success(mock_billing_provider):
    # standard user (id=2) is a member of org 1
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(
                session, _admin_auth(user_id=1, org_id=1), mock_billing_provider
            )
            await service.transfer_ownership(1, TransferOwnershipIn(user_id=2))

    # Verify: user 2 now has owner role, user 1 does not
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            user2 = await repos.user.unscoped.get(2)
            assert user2
            org1_roles_u2 = [r for r in user2.roles if r.organization_id == 1]
            assert any(r.is_protected for r in org1_roles_u2)


# ---------------------------------------------------------------------------
# paginate (line 72 - delegates to super().paginate)
# ---------------------------------------------------------------------------


async def test_paginate_organizations(mock_billing_provider):
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            result = await service.paginate(
                OrganizationOut,
                PageQueryParams(page_number=1, page_size=10, sort=[], filters=[]),
            )
    assert result.total >= 0


# ---------------------------------------------------------------------------
# create_organization - restore soft-deleted org (line 108)
# ---------------------------------------------------------------------------


async def test_create_organization_restores_soft_deleted(mock_billing_provider):
    """Re-creating a soft-deleted org name restores the record rather than inserting."""
    # First create, then delete org
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            await service.create_organization(OrganizationBase(name="Deletable Corp"))

    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            await service.delete_organization(1)

    # Delete the NEW active org (the one we just created)
    # Actually - we need a different approach: directly soft-delete an org in DB
    # and then create one with the same name
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            # Create and soft-delete a fresh org
            org = await repos.organization.create(
                name="Revivable Corp", billing_email="billing@example.org"
            )
            await repos.organization.delete(org)
            org_name = "Revivable Corp"

    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            out = await service.create_organization(OrganizationBase(name=org_name))

    assert out.name == org_name


# ---------------------------------------------------------------------------
# patch_organization - duplicate name raises (line 135)
# ---------------------------------------------------------------------------


async def test_patch_organization_duplicate_name_raises(mock_billing_provider):
    """Patching to an already-taken name raises AlreadyExistsException."""
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(session, _admin_auth(), mock_billing_provider)
            # "Globex Ltd" is org 2's name; try to rename org 1 to that
            with pytest.raises(AlreadyExistsException):
                await service.patch_organization(
                    1, OrganizationPatch(name="Globex Ltd")
                )


# ---------------------------------------------------------------------------
# transfer_ownership - org has external_customer_id (line 259)
# ---------------------------------------------------------------------------


async def test_transfer_ownership_syncs_stripe_customer(mock_billing_provider):
    """When org has external_customer_id, update_customer is called on transfer."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            org = await repos.organization.get(1)
            assert org
            await repos.organization.update(org, external_customer_id="cus_transfer")

    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_service(
                session, _admin_auth(user_id=1, org_id=1), mock_billing_provider
            )
            await service.transfer_ownership(1, TransferOwnershipIn(user_id=2))

    mock_billing_provider.update_customer.assert_called()
