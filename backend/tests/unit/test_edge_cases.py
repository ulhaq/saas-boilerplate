"""Targeted tests for specific coverage gaps not covered by other test files."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import insert

from src.platform.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    ValidationException,
)
from src.platform.core.security import Auth
from src.platform.enums import ComparisonOperator
from src.platform.enums import Permission as PermEnum
from src.platform.models.user_organization import UserOrganization
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.billing import CheckoutIn, StartTrialIn
from src.platform.schemas.common import FilterItem
from src.platform.schemas.organization import TransferOwnershipIn
from src.platform.schemas.permission import PermissionIn
from src.platform.schemas.user import ChangePasswordIn, CompleteInviteIn
from src.platform.services.billing import SubscriptionService, WebhookService
from src.platform.services.organization import OrganizationService
from src.platform.services.permission import PermissionService
from tests.conftest import TestSessionLocal


def _admin_auth(org_id: int = 1, user_id: int = 1) -> Auth:
    return Auth(
        id=user_id,
        name="Alice Owner",
        email="admin@example.org",
        organization_id=org_id,
        roles=["Owner"],
        permissions=[p.value for p in PermEnum],
    )


# ---------------------------------------------------------------------------
# schemas/user.py - validator raise paths
# ---------------------------------------------------------------------------


def test_change_password_in_passwords_do_not_match():
    """ChangePasswordIn.check_passwords_match raises when passwords differ (line 61)."""
    with pytest.raises(ValidationError):
        ChangePasswordIn(
            password="old", new_password="abc123!", confirm_password="xyz789!"
        )


def test_complete_invite_in_must_accept_terms():
    """
    CompleteInviteIn.must_accept_terms raises when accepted_terms=False (line 110)
    """
    with pytest.raises(ValidationError):
        CompleteInviteIn(invite_token="tok", terms_accepted=False)


# ---------------------------------------------------------------------------
# repositories/utils.py - BETWEEN filter operator (lines 129, 134, 154-155)
# ---------------------------------------------------------------------------


async def test_paginate_with_between_filter():
    """BETWEEN operator in get_filter_expression / cast_values_to_type."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.role.set_organization_scope(1)
            items, total = await repos.role.paginate(
                sort=["id"],
                filters=[
                    FilterItem(
                        field="id",
                        op=ComparisonOperator.BETWEEN,
                        values=["1", "3"],
                    )
                ],
                page_size=10,
                page_number=1,
            )
            assert total >= 1
            assert all(1 <= item.id <= 3 for item in items)


# ---------------------------------------------------------------------------
# repositories/user.py - has_other_user_with_role (lines 129-137)
# ---------------------------------------------------------------------------


async def test_has_other_user_with_role_returns_true():
    """Another user has role id=1 (Owner) when user 1 is excluded."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.user.set_organization_scope(1)
            # User 1 has Owner role (id=1); exclude user 2 > user 1 still has it
            result = await repos.user.has_other_user_with_role(
                role_id=1, exclude_user_id=2
            )
    assert result is True


async def test_has_other_user_with_role_returns_false():
    """No other user has the Owner role when user 1 is excluded."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.user.set_organization_scope(1)
            # Only user 1 has Owner role; exclude user 1 > nobody else
            result = await repos.user.has_other_user_with_role(
                role_id=1, exclude_user_id=1
            )
    assert result is False


# ---------------------------------------------------------------------------
# services/base.py - validation_callback branch (line 113)
# ---------------------------------------------------------------------------


async def test_delete_with_validation_callback_is_called():
    """ResourceService.delete() calls validation_callback when provided (line 113)."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = PermissionService(repos)
            perm = await service.create_permission(
                PermissionIn(name="callback:test_perm")
            )

            callback = AsyncMock()
            await service.delete(perm.id, validation_callback=callback)

    callback.assert_awaited_once()


# ---------------------------------------------------------------------------
# services/organization.py - continue when user is None (line 180)
# ---------------------------------------------------------------------------


async def test_delete_organization_skips_orphaned_membership():
    """
    delete_organization continues when a membership references a missing user (line 180)
    """
    # SQLite does not enforce FK constraints by default, so we can insert a
    # UserOrganization row whose user_id does not exist in the users table.
    async with TestSessionLocal() as session:
        async with session.begin():
            await session.execute(
                insert(UserOrganization).values(
                    user_id=99999,
                    organization_id=1,
                )
            )

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = OrganizationService(repos, _admin_auth(org_id=1), MagicMock())
            # Should not raise; the orphaned membership is silently skipped
            await service.delete_organization(1)


# ---------------------------------------------------------------------------
# services/organization.py - NotFoundException when owner role not found (line 250)
# ---------------------------------------------------------------------------


async def test_transfer_ownership_no_owner_role_raises(mock_billing_provider, mocker):
    """
    transfer_ownership raises NotFoundException when Owner role is missing (line 250)
    """
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = OrganizationService(repos, _admin_auth(), mock_billing_provider)

            # Simulate missing Owner role by patching the lookup
            mocker.patch.object(repos.role, "get_by_name", AsyncMock(return_value=None))

            with pytest.raises(NotFoundException):
                await service.transfer_ownership(1, TransferOwnershipIn(user_id=2))


# ---------------------------------------------------------------------------
# services/billing.py - post-lock AlreadyExistsException (line 139)
# ---------------------------------------------------------------------------


async def test_start_checkout_raises_post_lock_when_already_active(
    mock_billing_provider, plan_with_price, mocker
):
    """
    Race-condition guard: second get_active_for_organization_locked returns paid sub
    """
    price_id = plan_with_price["price"]["id"]

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())

            # Build a fake active paid subscription
            from src.platform.models.billing import PlanPrice, Subscription

            paid_price = PlanPrice()
            paid_price.amount = 999
            paid_sub = Subscription()
            paid_sub.status = "active"
            paid_sub.plan_price = paid_price

            # First call (pre-lock) > None to pass the initial check.
            # Second call (post-lock) > active paid sub to trigger line 139.
            mock_locked = AsyncMock(side_effect=[None, paid_sub])
            mocker.patch.object(
                repos.subscription,
                "get_active_for_organization_locked",
                mock_locked,
            )

            with pytest.raises(AlreadyExistsException):
                await service.start_checkout(CheckoutIn(plan_price_id=price_id))


# ---------------------------------------------------------------------------
# services/billing.py - post-lock ValidationException trial used (line 219)
# ---------------------------------------------------------------------------


async def test_start_trial_raises_post_lock_when_trial_already_used(
    mock_billing_provider, plan_with_price, mocker
):
    """Race-condition guard: org.trial_used becomes True after lock (line 219)."""
    price_id = plan_with_price["price"]["id"]
    mocker.patch("src.platform.services.billing.settings.billing_trial_period_days", 14)

    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            repos.subscription.set_organization_scope(1)
            service = SubscriptionService(repos, mock_billing_provider, _admin_auth())

            # Fetch real org first (trial_used=False) for the pre-lock call
            real_org = await repos.organization.get(1)

            # Fake org with trial_used=True for the post-lock re-check
            org_used = MagicMock()
            org_used.trial_used = True

            # First call > real org (trial_used=False, passes pre-lock check)
            # Second call > org_used (trial_used=True, triggers line 219)
            mock_get = AsyncMock(side_effect=[real_org, org_used])
            mocker.patch.object(repos.organization, "get", mock_get)

            with pytest.raises(ValidationException):
                await service.start_trial(StartTrialIn(plan_price_id=price_id))


# ---------------------------------------------------------------------------
# services/billing.py - early return when customer_id is None (line 682)
# ---------------------------------------------------------------------------


async def test_handle_payment_method_detached_no_customer_id(mock_billing_provider):
    """_handle_payment_method_detached returns early when no customer_id (line 682)."""
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = WebhookService(repos, mock_billing_provider)

            raw = {
                "data": {
                    "object": {"customer": None},
                    "previous_attributes": {},
                }
            }
            # Should complete without querying the database
            await service._handle_payment_method_detached(raw)

    # The organization repo must not have been touched
    mock_billing_provider.has_payment_method.assert_not_called()
