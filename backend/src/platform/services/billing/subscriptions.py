from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from src.platform.billing.dependencies import BillingProviderDep
from src.platform.core.config import settings
from src.platform.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    ValidationException,
)
from src.platform.core.hooks import HookEvent, emit
from src.platform.core.security import Auth
from src.platform.enums import AuditAction, ErrorCode
from src.platform.models.billing import PlanPrice, Subscription
from src.platform.models.organization import Organization
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.billing import (
    CheckoutIn,
    CheckoutOut,
    CustomerPortalOut,
    PlanSettingOut,
    StartTrialIn,
    SubscriptionOut,
    SwitchPlanIn,
    UpdateBillingEmailIn,
)
from src.platform.services.access import authenticate
from src.platform.services.base import BaseService
from src.platform.services.billing.common import _is_active_free_sub


class SubscriptionService(BaseService):
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        provider: BillingProviderDep,
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        self.provider = provider
        self.current_user = current_user
        super().__init__(repos)
        self.repos.subscription.set_organization_scope(current_user.organization_id)

    # Checkout and trial take no row or advisory locks: they only read local
    # state and call Stripe (which can be slow), and the subscription itself is
    # written later by the webhooks. Duplicate Stripe customers are prevented by
    # the provider's idempotency key, not by a lock.
    async def start_checkout(self, schema_in: CheckoutIn) -> CheckoutOut:
        price, external_price_id = await self._get_billable_price(
            schema_in.plan_price_id
        )
        await self._raise_if_subscribed()
        organization = await self._get_organization()

        # Do not touch the local subscription row here. The row is created or
        # updated by _handle_subscription_created once Stripe confirms the
        # subscription exists. This keeps start_checkout() a pure session
        # factory: it creates a Stripe checkout session and nothing else.
        # _handle_checkout_session_expired handles cleanup if checkout is
        # abandoned; since no row is changed here, that handler is a no-op for
        # free-plan users (status stays "active", not "incomplete").
        return await self._open_checkout_session(
            organization,
            price,
            external_price_id,
            trial_period_days=None,
            audit_action=AuditAction.BILLING_CHECKOUT_START,
        )

    async def start_trial(self, schema_in: StartTrialIn) -> CheckoutOut:
        price, external_price_id = await self._get_billable_price(
            schema_in.plan_price_id,
            free_price_error="Cannot start a trial on the free plan.",
        )

        if not settings.billing_trial_period_days:
            raise ValidationException("Trials are not configured.")

        organization = await self._get_organization()

        if organization.trial_used:
            raise ValidationException(
                "Trial has already been used.",
                error_code=ErrorCode.TRIAL_ALREADY_USED,
            )

        existing = await self.repos.subscription.get_active_for_organization(
            self.current_user.organization_id
        )
        if existing and existing.status in ("trialing", "past_due", "paused"):
            raise AlreadyExistsException(
                "Cannot start a trial while an active subscription exists.",
                error_code=ErrorCode.SUBSCRIPTION_ALREADY_ACTIVE,
            )
        if (
            existing
            and existing.status == "active"
            and existing.plan_price is not None
            and existing.plan_price.amount > 0
        ):
            raise AlreadyExistsException(
                "Cannot start a trial while an active paid subscription exists.",
                error_code=ErrorCode.SUBSCRIPTION_ALREADY_ACTIVE,
            )

        return await self._open_checkout_session(
            organization,
            price,
            external_price_id,
            trial_period_days=settings.billing_trial_period_days,
            audit_action=AuditAction.BILLING_TRIAL_START,
        )

    async def get_current_subscription(self) -> SubscriptionOut:
        sub = await self.repos.subscription.get_active_for_organization(
            self.current_user.organization_id
        )
        if not sub:
            raise NotFoundException(
                "No active subscription found for this organization.",
                error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
            )
        result = SubscriptionOut.model_validate(sub)
        organization = await self.repos.organization.get(
            self.current_user.organization_id
        )
        if organization:
            result.billing_email = organization.billing_email
            result.has_payment_method = organization.has_payment_method
            result.trial_used = organization.trial_used
        features = await self.repos.plan_feature.get_features_for_organization(
            self.current_user.organization_id
        )
        result.features = sorted(features)
        plan_settings = await self.repos.plan_setting.get_settings_for_organization(
            self.current_user.organization_id
        )
        result.plan_settings = [PlanSettingOut.model_validate(s) for s in plan_settings]
        return result

    async def set_billing_email(self, schema_in: UpdateBillingEmailIn) -> None:
        """Set the organization's billing email and push it to the billing
        provider so the Stripe customer stays in sync. The local DB is the
        source of truth; Stripe is a mirror."""
        organization = await self.repos.organization.get(
            self.current_user.organization_id
        )
        if not organization:
            raise NotFoundException("Organization not found.")

        await self.repos.organization.update(
            organization, billing_email=schema_in.billing_email
        )

        if organization.external_customer_id:
            await self.provider.update_customer(
                organization.external_customer_id,
                email=schema_in.billing_email,
            )

        await self.log_audit(
            AuditAction.BILLING_EMAIL_UPDATE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="organization",
            resource_id=organization.id,
        )

    async def cancel_subscription(self) -> SubscriptionOut:
        sub = await self._get_active_subscription()
        if sub.plan_price and sub.plan_price.amount == 0:
            raise ValidationException("You are already on the free plan.")
        if not sub.external_subscription_id:
            # Checkout was never completed - cancel locally, nothing to do in Stripe
            sub = await self.repos.subscription.update(
                sub,
                status="canceled",
                canceled_at=datetime.now(UTC),
            )
            return SubscriptionOut.model_validate(sub)

        ext_sub = await self.provider.cancel_subscription(sub.external_subscription_id)
        sub = await self.repos.subscription.update(
            sub,
            cancel_at_period_end=ext_sub.cancel_at_period_end,
            cancel_at=ext_sub.cancel_at,
            status=ext_sub.status,
        )
        await self.log_audit(
            AuditAction.BILLING_SUBSCRIPTION_CANCEL,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="subscription",
            resource_id=sub.id,
        )
        return SubscriptionOut.model_validate(sub)

    async def resume_subscription(self) -> SubscriptionOut:
        sub = await self._get_active_subscription()
        if not sub.cancel_at_period_end:
            raise ValidationException("Subscription is not scheduled for cancellation.")
        if not sub.external_subscription_id:
            raise ValidationException(
                "Subscription is not yet active in billing provider."
            )

        ext_sub = await self.provider.resume_subscription(sub.external_subscription_id)
        sub = await self.repos.subscription.update(
            sub,
            cancel_at_period_end=ext_sub.cancel_at_period_end,
            cancel_at=ext_sub.cancel_at,
            status=ext_sub.status,
        )
        await self.log_audit(
            AuditAction.BILLING_SUBSCRIPTION_RESUME,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="subscription",
            resource_id=sub.id,
        )
        return SubscriptionOut.model_validate(sub)

    async def switch_plan(self, schema_in: SwitchPlanIn) -> SubscriptionOut:
        sub = await self._get_active_subscription()
        if not sub.external_subscription_id:
            raise ValidationException(
                "Cannot switch plans from the free tier. "
                "Use checkout to subscribe to a paid plan."
            )

        price, external_price_id = await self._get_billable_price(
            schema_in.plan_price_id,
            free_price_error=(
                "Cannot switch to the free plan. "
                "Cancel your subscription to return to the free tier."
            ),
        )

        if sub.plan_price_id == price.id:
            raise ValidationException("Subscription is already on this plan.")

        old_plan_price_id = sub.plan_price_id
        ext_sub = await self.provider.switch_subscription_price(
            sub.external_subscription_id,
            external_price_id,
            skip_proration=False,
            new_amount=price.amount,
        )
        # This is the authoritative write for a plan switch: the values come
        # from Stripe's synchronous API response, and PLAN_CHANGED is emitted
        # here. The customer.subscription.updated webhook that Stripe fires
        # for the same switch acts as a healer - it only writes (and only
        # emits PLAN_CHANGED) if local state still differs, e.g. because this
        # transaction failed to commit after the Stripe call succeeded.
        sub = await self.repos.subscription.update(
            sub,
            plan_price_id=price.id,
            status=ext_sub.status,
        )
        await emit(
            HookEvent.PLAN_CHANGED,
            repos=self.repos,
            organization_id=self.current_user.organization_id,
        )
        await self.log_audit(
            AuditAction.BILLING_PLAN_SWITCH,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="subscription",
            resource_id=sub.id,
            details={
                "from_plan_price_id": old_plan_price_id,
                "to_plan_price_id": price.id,
            },
        )
        return SubscriptionOut.model_validate(sub)

    async def get_customer_portal_url(self) -> CustomerPortalOut:
        organization = await self.repos.organization.get(
            self.current_user.organization_id
        )
        if not organization or not organization.external_customer_id:
            raise ValidationException(
                "No billing customer found for this organization."
            )

        result = await self.provider.get_customer_portal_url(
            external_customer_id=organization.external_customer_id,
            return_url=settings.billing_portal_return_url,
        )
        return CustomerPortalOut(portal_url=result.portal_url)

    async def _get_billable_price(
        self, plan_price_id: int, *, free_price_error: str | None = None
    ) -> tuple[PlanPrice, str]:
        """The active, provider-synced price, with its external price id.

        `free_price_error` rejects the free price with that message, checked
        between the inactive and not-synced checks.
        """
        price = await self.repos.plan_price.get(plan_price_id)
        if not price or not price.is_active:
            raise NotFoundException(
                f"Plan price not found or inactive. [id={plan_price_id}]"
            )
        if free_price_error is not None and price.amount == 0:
            raise ValidationException(free_price_error)
        if not price.external_price_id:
            raise NotFoundException("Plan price is not synced with billing provider.")
        return price, price.external_price_id

    async def _get_organization(self) -> Organization:
        organization = await self.repos.organization.get(
            self.current_user.organization_id
        )
        if not organization:
            raise NotFoundException("Organization not found.")
        return organization

    async def _raise_if_subscribed(self) -> None:
        """Checkout is for organizations without a paid subscription - an
        active free subscription doesn't count."""
        existing = await self.repos.subscription.get_active_for_organization(
            self.current_user.organization_id
        )
        if (
            existing
            and existing.status in ("active", "trialing", "past_due", "paused")
            and not _is_active_free_sub(existing)
        ):
            raise AlreadyExistsException(
                "Organization already has an active subscription.",
                error_code=ErrorCode.SUBSCRIPTION_ALREADY_ACTIVE,
            )

    async def _open_checkout_session(
        self,
        organization: Organization,
        price: PlanPrice,
        external_price_id: str,
        *,
        trial_period_days: int | None,
        audit_action: AuditAction,
    ) -> CheckoutOut:
        """Create the provider customer if needed, open a checkout session for
        `price`, and audit it."""
        external_customer_id = organization.external_customer_id
        if not external_customer_id:
            external_customer_id = await self.provider.get_or_create_customer(
                organization_id=self.current_user.organization_id,
                organization_name=organization.name,
                email=organization.billing_email,
            )
            await self.repos.organization.update(
                organization, external_customer_id=external_customer_id
            )

        metadata = {
            "organization_id": str(self.current_user.organization_id),
            "plan_price_id": str(price.id),
        }
        result = await self.provider.create_checkout_session(
            external_customer_id=external_customer_id,
            external_price_id=external_price_id,
            amount=price.amount,
            success_url=settings.billing_success_url,
            cancel_url=settings.billing_cancel_url,
            metadata=metadata,
            trial_period_days=trial_period_days,
        )
        await self.log_audit(
            audit_action,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="subscription",
            details={"plan_price_id": price.id},
        )
        return CheckoutOut(checkout_url=result.checkout_url)

    async def _get_active_subscription(self) -> Subscription:
        sub = await self.repos.subscription.get_active_for_organization_locked(
            self.current_user.organization_id
        )
        if not sub:
            raise NotFoundException(
                "No active subscription found for this organization.",
                error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
            )
        return sub
