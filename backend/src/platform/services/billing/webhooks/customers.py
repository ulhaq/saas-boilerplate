from src.platform.services.billing.webhooks.base import (
    WebhookHandler,
    WebhookHandlerGroup,
)


class CustomerWebhookHandlers(WebhookHandlerGroup):
    """Customer details and payment methods mirrored onto the organization."""

    def handlers(self) -> dict[str, WebhookHandler]:
        return {
            "customer.updated": self._handle_customer_updated,
            "payment_method.attached": self._handle_payment_method_attached,
            "payment_method.detached": self._handle_payment_method_detached,
        }

    async def _handle_customer_updated(self, raw: dict) -> None:
        # Safety net: the app is the source of truth for billing_email, but a
        # user editing their email in the Stripe customer portal would otherwise
        # silently diverge. Pull Stripe's email back in so the two stay in sync.
        obj = raw["data"]["object"]
        customer_id: str | None = obj.get("id")
        email: str | None = obj.get("email")
        # billing_email is a required field - never let an empty Stripe email
        # clear it.
        if not customer_id or not email:
            return
        organization = await self.repos.organization.get_by_external_customer_id_locked(
            customer_id
        )
        if organization and organization.billing_email != email:
            await self.repos.organization.update(organization, billing_email=email)

    async def _handle_payment_method_attached(self, raw: dict) -> None:
        customer_id: str | None = raw["data"]["object"].get("customer")
        if not customer_id:
            return
        organization = await self.repos.organization.get_by_external_customer_id_locked(
            customer_id
        )
        if organization:
            await self.repos.organization.update(organization, has_payment_method=True)

    async def _handle_payment_method_detached(self, raw: dict) -> None:
        # payment_method.detached clears the customer field, so we get it from
        # the previous attributes snapshot Stripe includes in the event.
        prev = raw["data"].get("previous_attributes", {})
        customer_id: str | None = raw["data"]["object"].get("customer") or prev.get(
            "customer"
        )
        if not customer_id:
            return
        organization = await self.repos.organization.get_by_external_customer_id_locked(
            customer_id
        )
        if organization and organization.has_payment_method:
            has_more = await self.provider.has_payment_method(customer_id)
            await self.repos.organization.update(
                organization, has_payment_method=has_more
            )
