"""Billing's ORGANIZATION_CREATED handler: the billing account and free subscription."""

from src.billing.repositories.manager import BillingRepositoryManager
from src.platform.services.organization import setup_new_organization
from tests.conftest import TestSessionLocal


async def test_setup_new_organization_creates_roles_and_billing():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = BillingRepositoryManager(session)

            # Create a fresh org + user
            org = await repos.organization.create(name="Fresh Org")
            user = await repos.user.create(
                name="Fresh User",
                email="fresh@example.com",
                password="hashed",
                terms_accepted_at=None,
            )

            await setup_new_organization(repos, org, user)

            # After setup: Owner role should exist for this org
            roles = await repos.role.unscoped.get_all()
            org_roles = [r for r in roles if r.organization_id == org.id]
            assert any(r.is_protected for r in org_roles), (
                "Owner role should be created"
            )

            # Billing (via ORGANIZATION_CREATED) opened an account billed to
            # the owner, on the free plan.
            account = await repos.billing_account.get_for_organization(org.id)
            assert account is not None
            assert account.billing_email == "fresh@example.com"
            sub = await repos.subscription.get_active_for_organization(org.id)
            assert sub is not None
            assert sub.status == "active"


async def test_setup_new_organization_no_free_plan_logs_warning(caplog):
    """
    When no free price exists, billing's ORGANIZATION_CREATED handler logs a
    warning and skips sub creation.
    """
    import logging

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = BillingRepositoryManager(session)

            # Remove the free price by deactivating it
            prices = await repos.plan_price.get_all()
            for price in prices:
                if price.amount == 0:
                    await repos.plan_price.update(price, is_active=False)

            org = await repos.organization.create(name="No Free Plan Org")
            user = await repos.user.create(
                name="Nofree User",
                email="nofree@example.com",
                password="hashed",
                terms_accepted_at=None,
            )

            org_logger = "src.billing.hooks"
            with caplog.at_level(logging.WARNING, logger=org_logger):
                await setup_new_organization(repos, org, user)

            assert any("free plan" in r.message.lower() for r in caplog.records)

            # No subscription created for this org
            sub = await repos.subscription.get_active_for_organization(org.id)
            assert sub is None
