import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from src.billing.enums import LIVE_STATUSES, BillingAuditAction
from src.billing.models.billing import PlanPrice, Subscription
from src.billing.provider.abc import BillingProviderABC
from src.billing.repositories.manager import BillingRepositoryManager
from src.billing.services.base import BillingBaseService
from src.billing.services.common import notify_subscription_managers
from src.platform.core.config import settings
from src.platform.core.hooks import HookEvent, emit

log = logging.getLogger(__name__)

WebhookHandler = Callable[[dict], Awaitable[None]]


class WebhookHandlerGroup(BillingBaseService):
    """A family of webhook event handlers, plus the helpers they share.

    Each subclass maps the provider event types it owns to handler methods via
    ``handlers()``; ``WebhookService`` merges every group into one dispatch
    table. Handlers run inside the webhook request's transaction.
    """

    def __init__(
        self,
        repos: BillingRepositoryManager,
        provider: BillingProviderABC,
    ) -> None:
        self.provider = provider
        super().__init__(repos)

    def handlers(self) -> dict[str, WebhookHandler]:
        raise NotImplementedError

    async def _plan_changed(self, organization_id: int) -> None:
        """Notify domain modules (via hooks) that the org's plan state changed,
        so they can reconcile plan-limited resources."""
        await emit(
            HookEvent.PLAN_CHANGED,
            repos=self.repos,
            organization_id=organization_id,
        )

    async def _notify_subscription_managers(
        self,
        organization_id: int,
        email_template: str,
        data: dict,
    ) -> None:
        organization = await self.repos.organization.get(organization_id)
        if not organization:
            return
        await notify_subscription_managers(
            self.repos,
            organization,
            email_template,
            data,
        )

    async def _notify_payment_uncollectible(self, sub: Subscription) -> None:
        await self._notify_subscription_managers(
            sub.organization_id,
            "payment-uncollectible",
            {"billing_url": f"{settings.frontend_url}/settings/billing"},
        )

    async def _downgrade_to_free(
        self,
        sub: Subscription,
        *,
        cancel_remote: bool = True,
    ) -> PlanPrice | None:
        """
        Cancels the Stripe subscription then downgrades the local record to the
        free plan. The Stripe call is made first so that, on failure, the
        BillingProviderException propagates to the webhook handler and Stripe
        retries - keeping external_subscription_id intact for the retry.
        Local state is only mutated after a successful Stripe cancellation.

        Clearing external_subscription_id after deletion prevents the
        customer.subscription.deleted webhook (fired synchronously by Stripe)
        from finding and re-canceling the row; the row lock held by this
        transaction serializes that webhook behind our update.

        Pass cancel_remote=False when the Stripe subscription is already in a
        terminal state (e.g. incomplete_expired) and cannot be canceled via
        the API.

        If no free price is configured the subscription is canceled outright.
        """
        free_price = await self.repos.plan_price.get_free_price()
        if not free_price:
            log.error(
                "No free price configured; canceling subscription directly [sub_id=%s]",
                sub.external_subscription_id,
            )
            if cancel_remote and sub.external_subscription_id:
                # Allow BillingProviderException to propagate so Stripe retries.
                await self.provider.delete_subscription(sub.external_subscription_id)
            await self.repos.subscription.update(
                sub,
                status="canceled",
                canceled_at=datetime.now(UTC),
            )
            return None

        if cancel_remote and sub.external_subscription_id:
            # Stripe-first: if this raises, local state is unchanged and the
            # webhook will be retried with external_subscription_id still set.
            await self.provider.delete_subscription(sub.external_subscription_id)

        # Stripe subscription is gone - update local record to free plan.
        # Clearing external_subscription_id prevents the customer.subscription.deleted
        # webhook from finding this row and marking it canceled.
        await self.repos.subscription.update(
            sub,
            plan_price_id=free_price.id,
            status="active",
            external_subscription_id=None,
            current_period_start=None,
            current_period_end=None,
            canceled_at=None,
            cancel_at=None,
            cancel_at_period_end=False,
        )
        await self._plan_changed(sub.organization_id)

        return free_price

    @staticmethod
    def _tracks_another_subscription(
        sub: Subscription,
        external_subscription_id: str,
    ) -> bool:
        """Whether the organization's row already follows a different live Stripe
        subscription - making `external_subscription_id` a duplicate (e.g. the
        checkout was paid in two browser tabs)."""
        return (
            sub.external_subscription_id is not None
            and sub.external_subscription_id != external_subscription_id
            and sub.status in LIVE_STATUSES
        )

    async def _cancel_duplicate_subscription(
        self,
        organization_id: int,
        external_subscription_id: str,
    ) -> None:
        """Refund and cancel a duplicate subscription, leaving the organization on
        the one it already has."""
        refunded = await self.provider.cancel_duplicate_subscription(
            external_subscription_id,
        )
        log.warning(
            "Duplicate subscription refunded and canceled "
            "[organization_id=%s external_subscription_id=%s refunded=%s]",
            organization_id,
            external_subscription_id,
            refunded,
        )
        await self.log_audit(
            BillingAuditAction.BILLING_DUPLICATE_SUBSCRIPTION_REFUNDED,
            organization_id=organization_id,
            resource_type="subscription",
            details={
                "external_subscription_id": external_subscription_id,
                "refunded_amount": refunded,
            },
        )
        await self._notify_subscription_managers(
            organization_id,
            "duplicate-subscription-refunded",
            {"billing_url": f"{settings.frontend_url}/settings/billing"},
        )
