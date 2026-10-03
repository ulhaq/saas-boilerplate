"""Billing refuses to delete an organization with a paid subscription."""

import pytest

from src.billing.repositories.manager import BillingRepositoryManager
from src.platform.core.exceptions import (
    PermissionDeniedException,
)
from src.platform.core.security import Auth
from src.platform.enums import Permission as PermEnum
from src.platform.repositories.repository_manager import RepositoryManager
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


def _make_service(session, auth: Auth) -> OrganizationService:
    repos = RepositoryManager(session)
    return OrganizationService(repos, auth)


async def test_delete_organization_with_active_subscription_raises(plan_with_price):
    price_id = plan_with_price["price"]["id"]
    async with TestSessionLocal() as session, session.begin():
        repos = BillingRepositoryManager(session)
        sub = await repos.subscription.get_active_for_organization(1)
        assert sub
        await repos.subscription.update(
            sub,
            plan_price_id=price_id,
            external_subscription_id="sub_block_del",
        )

    async with TestSessionLocal() as session, session.begin():
        service = _make_service(session, _admin_auth(org_id=1))
        with pytest.raises(PermissionDeniedException):
            await service.delete_organization(1)
