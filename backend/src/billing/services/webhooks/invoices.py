from src.billing.models.billing import Subscription
from src.billing.services.webhooks.base import (
    WebhookHandler,
    WebhookHandlerGroup,
)
from src.foundation.core.config import settings


class InvoiceWebhookHandlers(WebhookHandlerGroup):
    """Invoice payment outcomes and charge disputes."""

    def handlers(self) -> dict[str, WebhookHandler]:
        return {
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            "invoice.payment_succeeded": self._handle_invoice_payment_succeeded,
            "invoice.payment_action_required": (
                self._handle_invoice_payment_action_required
            ),
            "invoice.marked_uncollectible": self._handle_invoice_marked_uncollectible,
            "charge.dispute.created": self._handle_charge_dispute_created,
        }

    async def _get_subscription_from_invoice(self, obj: dict) -> Subscription | None:
        parent = obj.get("parent") or {}
        sub_details = parent.get("subscription_details") or {}
        sub_id: str | None = sub_details.get("subscription") or obj.get("subscription")
        if sub_id:
            return await self.repos.subscription.get_by_external_subscription_id_locked(
                sub_id,
            )
        customer_id: str | None = obj.get("customer")
        if customer_id:
            account = (
                await self.repos.billing_account.get_by_external_customer_id_locked(
                    customer_id,
                )
            )
            if account:
                return await self.repos.subscription.get_active_for_organization_locked(
                    account.organization_id,
                )
        return None

    async def _notify_payment_failed(self, sub: Subscription) -> None:
        await self._notify_subscription_managers(
            sub.organization_id,
            "payment-failed",
            {"billing_url": f"{settings.frontend_url}/settings/billing"},
        )

    async def _handle_invoice_payment_failed(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        sub = await self._get_subscription_from_invoice(obj)
        if not sub:
            return
        # Mirror Stripe's past_due transition locally in case the matching
        # customer.subscription.updated event is delayed or lost. Access is
        # unaffected: past_due counts as active in entitlement queries until
        # invoice.marked_uncollectible downgrades the org to free.
        if sub.status == "active" and sub.external_subscription_id:
            await self.repos.subscription.update(sub, status="past_due")
        await self._notify_payment_failed(sub)

    async def _handle_invoice_payment_succeeded(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        sub = await self._get_subscription_from_invoice(obj)
        if not sub:
            return
        if sub.status in ("past_due", "incomplete"):
            await self.repos.subscription.update(sub, status="active")

    async def _handle_invoice_payment_action_required(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        sub = await self._get_subscription_from_invoice(obj)
        if not sub:
            return

        await self._notify_subscription_managers(
            sub.organization_id,
            "payment-action-required",
            {"billing_url": f"{settings.frontend_url}/settings/billing"},
        )

    async def _handle_invoice_marked_uncollectible(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        sub = await self._get_subscription_from_invoice(obj)
        if not sub:
            return

        await self._downgrade_to_free(sub)
        await self._notify_payment_uncollectible(sub)

    async def _handle_charge_dispute_created(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        charge_id: str | None = obj.get("charge")
        if not charge_id:
            return
        # The dispute object carries no customer reference - resolve it
        # through the disputed charge.
        customer_id = await self.provider.get_charge_customer(charge_id)
        if not customer_id:
            return
        account = await self.repos.billing_account.get_by_external_customer_id_locked(
            customer_id,
        )
        if not account:
            return
        sub = await self.repos.subscription.get_active_for_organization_locked(
            account.organization_id,
        )
        if not sub:
            return

        # A dispute means the payment is contested, not yet lost. Flag the
        # subscription as past_due - access is retained and the frontend
        # banner prompts the managers - and notify them. If the dispute is
        # lost, Stripe cancels the subscription or marks the invoice
        # uncollectible, and those handlers remove paid access.
        if sub.status == "active" and sub.external_subscription_id:
            await self.repos.subscription.update(sub, status="past_due")
        await self._notify_payment_failed(sub)
