import logging
from datetime import UTC, datetime

from src.billing.models.account import BillingAccount
from src.billing.services.webhooks.base import (
    WebhookHandler,
    WebhookHandlerGroup,
)

log = logging.getLogger(__name__)


class CheckoutWebhookHandlers(WebhookHandlerGroup):
    def handlers(self) -> dict[str, WebhookHandler]:
        return {
            "checkout.session.completed": self._handle_checkout_completed,
            "checkout.session.expired": self._handle_checkout_session_expired,
        }

    async def _get_account_from_checkout_event(
        self, obj: dict
    ) -> BillingAccount | None:
        customer_id: str | None = obj.get("customer")
        metadata: dict = obj.get("metadata", {})

        account = None
        if customer_id:
            account = (
                await self.repos.billing_account.get_by_external_customer_id_locked(
                    customer_id
                )
            )
        if not account:
            organization_id_str = metadata.get("organization_id")
            if organization_id_str:
                try:
                    account = await self.repos.billing_account.get_for_organization(
                        int(organization_id_str)
                    )
                except ValueError:
                    log.warning(
                        "Invalid organization_id in checkout metadata [value=%r]",
                        organization_id_str,
                    )
        return account

    async def _handle_checkout_completed(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        subscription_id: str | None = obj.get("subscription")
        metadata: dict = obj.get("metadata", {})

        customer_id: str | None = obj.get("customer")
        if not subscription_id or not customer_id:
            return

        # Try to find existing subscription row by customer or metadata organization_id
        account = await self._get_account_from_checkout_event(obj)
        if not account:
            return

        # If we fell back to the metadata lookup the organization
        # has no external_customer_id yet.
        # Stamp it now so future webhook events can
        # find the organization by customer ID.
        if not account.external_customer_id:
            await self.repos.billing_account.update(
                account, external_customer_id=customer_id
            )

        sub = await self.repos.subscription.get_active_for_organization_locked(
            account.organization_id
        )
        if not sub:
            return
        if self._tracks_another_subscription(sub, subscription_id):
            # A duplicate: customer.subscription.created refunds and cancels it
            # (whichever of the two events arrives first, the row is untouched).
            return

        plan_price_id_str = metadata.get("plan_price_id")
        updates: dict = {
            "external_subscription_id": subscription_id,
        }
        if plan_price_id_str:
            try:
                updates["plan_price_id"] = int(plan_price_id_str)
            except ValueError:
                log.warning(
                    "Invalid plan_price_id in checkout metadata, skipping "
                    "[value=%r sub_id=%s]",
                    plan_price_id_str,
                    subscription_id,
                )

        await self.repos.subscription.update(sub, **updates)

    async def _handle_checkout_session_expired(self, raw: dict) -> None:
        obj = raw["data"]["object"]

        account = await self._get_account_from_checkout_event(obj)
        sub = None
        if account:
            sub = await self.repos.subscription.get_active_for_organization_locked(
                account.organization_id
            )

        if not sub or sub.status != "incomplete":
            return

        # Restore to the free plan rather than canceling outright. The incomplete
        # row was either a brand-new user or an existing free user who abandoned
        # checkout; in both cases the right state is an active free subscription.
        free_price = await self.repos.plan_price.get_free_price()
        if free_price:
            await self.repos.subscription.update(
                sub,
                status="active",
                plan_price_id=free_price.id,
                external_subscription_id=None,
                canceled_at=None,
                cancel_at=None,
                cancel_at_period_end=False,
            )
            await self._plan_changed(sub.organization_id)
        else:
            await self.repos.subscription.update(
                sub, status="canceled", canceled_at=datetime.now(UTC)
            )
