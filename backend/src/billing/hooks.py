"""Billing's handlers for the foundation's organization lifecycle hooks.

Listed in `src.billing.module` and installed by the composition root
(`src.bootstrap`). Each runs in the caller's transaction, through
``BillingRepositoryManager(repos.db)``.
"""

import logging

from src.billing.enums import BillingErrorCode
from src.billing.repositories.manager import BillingRepositoryManager
from src.foundation.core.exceptions import PermissionDeniedException
from src.foundation.repositories.repository_manager import RepositoryManager

log = logging.getLogger(__name__)


async def open_billing_account(
    *,
    repos: RepositoryManager,
    organization_id: int,
    user_id: int,
) -> None:
    """Give a new organization its billing account, billed to its owner, and a
    local free subscription. No Stripe customer is created here - that happens
    when the organization starts a trial or a paid checkout."""
    billing = BillingRepositoryManager(repos.db)
    # A restored organization keeps the account it had.
    if not await billing.billing_account.filter_by(organization_id=organization_id):
        owner = await repos.user.unscoped.get_one(user_id)
        await billing.billing_account.create(
            organization_id=organization_id,
            billing_email=owner.email,
        )

    free_price = await billing.plan_price.get_free_price()
    if free_price:
        await billing.subscription.create(
            organization_id=organization_id,
            plan_price_id=free_price.id,
            status="active",
        )
    else:
        log.warning(
            "No free plan found - skipping auto-subscription for organization %s",
            organization_id,
        )


async def refuse_deleting_a_paying_organization(
    *,
    repos: RepositoryManager,
    organization_id: int,
) -> None:
    billing = BillingRepositoryManager(repos.db)
    subscription = await billing.subscription.get_active_for_organization(
        organization_id,
    )
    if subscription and subscription.external_subscription_id:
        raise PermissionDeniedException(
            "Cannot delete an organization with an active subscription."
            " Cancel the subscription first.",
            error_code=BillingErrorCode.SUBSCRIPTION_ALREADY_ACTIVE,
        )


async def bill_the_new_owner(
    *,
    repos: RepositoryManager,
    organization_id: int,
    user_id: int,
) -> None:
    """Point the provider customer's email at the new owner - via the worker's
    customer sync (`run_customer_sync_loop`), so a provider outage can't fail
    the transfer. Stripe's `customer.updated` webhook then brings the email
    into the local billing email."""
    billing = BillingRepositoryManager(repos.db)
    account = await billing.billing_account.get_for_organization(organization_id)
    if account and account.external_customer_id:
        new_owner = await repos.user.unscoped.get_one(user_id)
        # A new email starts its retries fresh.
        await billing.billing_account.update(
            account,
            pending_customer_email=new_owner.email,
            customer_sync_attempts=0,
            customer_sync_next_at=None,
        )
