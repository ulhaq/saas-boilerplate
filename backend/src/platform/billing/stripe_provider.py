import hashlib
from datetime import UTC, datetime
from typing import Literal

import stripe

from src.platform.billing.abc import BillingProviderABC
from src.platform.billing.types import (
    CheckoutResult,
    CustomerPortalResult,
    ExternalPrice,
    ExternalProduct,
    ExternalSubscription,
    WebhookPayload,
)
from src.platform.core.config import settings
from src.platform.core.exceptions import (
    BillingProviderException,
    BillingWebhookException,
)


def _ts_to_dt(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=UTC)


class StripeProvider(BillingProviderABC):
    def __init__(self, api_key: str, webhook_secret: str) -> None:
        self._api_key = api_key
        self._webhook_secret = webhook_secret

    @staticmethod
    def _idempotency_key(*parts: str) -> str:
        raw = ":".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:40]

    async def search_product_by_name(self, name: str) -> ExternalProduct | None:
        try:
            escaped = name.replace("'", "\\'")
            for active in ("true", "false"):
                results = await stripe.Product.search_async(
                    query=f"active:'{active}' AND name:'{escaped}'",
                    limit=1,
                    api_key=self._api_key,
                )
                for p in results.data:
                    return ExternalProduct(external_id=p.id, is_active=p.active)
            return None
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def create_product(
        self, name: str, description: str | None
    ) -> ExternalProduct:
        try:
            params: dict = {"name": name}
            if description:
                params["description"] = description
            product = await stripe.Product.create_async(
                **params,
                idempotency_key=self._idempotency_key(
                    "product-create", name, description or ""
                ),
                api_key=self._api_key,
            )
            return ExternalProduct(external_id=product.id)
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def update_product(
        self, external_product_id: str, name: str, description: str | None
    ) -> ExternalProduct:
        try:
            params: dict = {"name": name}
            if description is not None:
                params["description"] = description
            product = await stripe.Product.modify_async(
                external_product_id,
                **params,
                api_key=self._api_key,
            )
            return ExternalProduct(external_id=product.id, is_active=product.active)
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def reactivate_product(self, external_product_id: str) -> None:
        try:
            await stripe.Product.modify_async(
                external_product_id,
                active=True,
                api_key=self._api_key,
            )
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def archive_product(self, external_product_id: str) -> None:
        try:
            await stripe.Product.modify_async(
                external_product_id,
                active=False,
                api_key=self._api_key,
            )
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def search_price(
        self,
        external_product_id: str,
        amount: int,
        currency: str,
        interval: Literal["day", "month", "week", "year"],
        interval_count: int,
    ) -> ExternalPrice | None:
        try:
            base = f"product:'{external_product_id}' AND currency:'{currency}'"
            for active in ("true", "false"):
                results = await stripe.Price.search_async(
                    query=f"active:'{active}' AND {base}",
                    limit=100,
                    api_key=self._api_key,
                )
                for p in results.data:
                    recurring = p.recurring
                    if (
                        p.unit_amount == amount
                        and recurring is not None
                        and recurring.interval == interval
                        and recurring.interval_count == interval_count
                    ):
                        return ExternalPrice(external_id=p.id, is_active=p.active)
            return None
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def create_price(
        self,
        external_product_id: str,
        amount: int,
        currency: str,
        interval: Literal["day", "month", "week", "year"],
        interval_count: int,
        tax_behavior: Literal["exclusive", "inclusive", "unspecified"] = "exclusive",
    ) -> ExternalPrice:
        try:
            price = await stripe.Price.create_async(
                product=external_product_id,
                unit_amount=amount,
                currency=currency,
                recurring={
                    "interval": interval,
                    "interval_count": interval_count,
                },
                tax_behavior=tax_behavior,
                idempotency_key=self._idempotency_key(
                    "price-create",
                    external_product_id,
                    str(amount),
                    currency,
                    interval,
                    str(interval_count),
                    tax_behavior,
                ),
                api_key=self._api_key,
            )
            return ExternalPrice(external_id=price.id, is_active=price.active)
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def archive_price(self, external_price_id: str) -> None:
        try:
            await stripe.Price.modify_async(
                external_price_id,
                active=False,
                api_key=self._api_key,
            )
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def get_or_create_customer(
        self, organization_id: int, organization_name: str, email: str | None = None
    ) -> str:
        try:
            existing = await stripe.Customer.search_async(
                query=f'metadata["organization_id"]:"{organization_id}"',
                api_key=self._api_key,
            )
            if existing.data:
                return existing.data[0].id

            params: dict = {
                "name": organization_name,
                "metadata": {"organization_id": str(organization_id)},
            }
            if email:
                params["email"] = email
            customer = await stripe.Customer.create_async(
                **params, api_key=self._api_key
            )
            return customer.id
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def update_customer(
        self,
        external_customer_id: str,
        email: str | None = None,
        name: str | None = None,
    ) -> None:
        fields: dict = {}
        if email is not None:
            fields["email"] = email
        if name is not None:
            fields["name"] = name
        if not fields:
            return
        try:
            await stripe.Customer.modify_async(
                external_customer_id,
                **fields,
                api_key=self._api_key,
            )
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def create_checkout_session(
        self,
        external_customer_id: str | None,
        external_price_id: str,
        amount: int,
        success_url: str,
        cancel_url: str,
        metadata: dict,
        trial_period_days: int | None = None,
    ) -> CheckoutResult:
        try:
            params: dict = {
                "mode": "subscription",
                "line_items": [{"price": external_price_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "billing_address_collection": "required",
                "tax_id_collection": {"enabled": True},
                "metadata": {k: str(v) for k, v in metadata.items()},
            }
            if amount == 0 or trial_period_days:
                params["payment_method_collection"] = "if_required"
            if external_customer_id:
                params["customer"] = external_customer_id
            else:
                params["customer_creation"] = "always"

            if trial_period_days:
                params["subscription_data"] = {
                    "trial_period_days": trial_period_days,
                    "trial_settings": {
                        "end_behavior": {"missing_payment_method": "pause"}
                    },
                }

            if external_customer_id:
                params["customer_update"] = {"address": "auto", "name": "auto"}

            if settings.billing_automatic_tax:
                params["automatic_tax"] = {"enabled": True}

            session = await stripe.checkout.Session.create_async(
                **params,
                api_key=self._api_key,
            )
            return CheckoutResult(
                checkout_url=session.url or "",
                external_session_id=session.id,
            )
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def cancel_subscription(
        self, external_subscription_id: str
    ) -> ExternalSubscription:
        try:
            sub = await stripe.Subscription.modify_async(
                external_subscription_id,
                cancel_at_period_end=True,
                api_key=self._api_key,
            )
            return self._map_subscription(sub)
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def delete_subscription(self, external_subscription_id: str) -> None:
        try:
            await stripe.Subscription.cancel_async(
                external_subscription_id,
                api_key=self._api_key,
            )
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def resume_subscription(
        self, external_subscription_id: str
    ) -> ExternalSubscription:
        try:
            current = await stripe.Subscription.retrieve_async(
                external_subscription_id,
                api_key=self._api_key,
            )
            if current.status == "paused":
                sub = await stripe.Subscription.resume_async(
                    external_subscription_id,
                    billing_cycle_anchor="unchanged",
                    api_key=self._api_key,
                )
            else:
                sub = await stripe.Subscription.modify_async(
                    external_subscription_id,
                    cancel_at_period_end=False,
                    api_key=self._api_key,
                )
            return self._map_subscription(sub)
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def switch_subscription_price(
        self,
        external_subscription_id: str,
        new_external_price_id: str,
        skip_proration: bool = False,
        new_amount: int = 0,
    ) -> ExternalSubscription:
        try:
            sub = await stripe.Subscription.retrieve_async(
                external_subscription_id,
                api_key=self._api_key,
            )
            if not sub.items.data:
                raise BillingProviderException("Subscription has no items to update.")
            item_id: str = sub.items.data[0].id
            modify_params: dict = {
                "items": [{"id": item_id, "price": new_external_price_id}],
                "proration_behavior": "none" if skip_proration else "create_prorations",
            }
            if settings.billing_automatic_tax:
                modify_params["automatic_tax"] = {"enabled": new_amount > 0}
            updated = await stripe.Subscription.modify_async(
                external_subscription_id,
                **modify_params,
                api_key=self._api_key,
            )
            return self._map_subscription(updated)
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def create_subscription(
        self,
        external_customer_id: str,
        external_price_id: str,
        trial_period_days: int | None = None,
    ) -> ExternalSubscription:
        try:
            params: dict = {
                "customer": external_customer_id,
                "items": [{"price": external_price_id}],
                "idempotency_key": self._idempotency_key(
                    "sub-create",
                    external_customer_id,
                    external_price_id,
                    str(trial_period_days or ""),
                ),
                "api_key": self._api_key,
            }
            if trial_period_days:
                params["trial_period_days"] = trial_period_days
                params["trial_settings"] = {
                    "end_behavior": {"missing_payment_method": "pause"}
                }
            sub = await stripe.Subscription.create_async(**params)
            return self._map_subscription(sub)
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def has_payment_method(self, external_customer_id: str) -> bool:
        try:
            pms = await stripe.PaymentMethod.list_async(
                customer=external_customer_id,
                limit=1,
                api_key=self._api_key,
            )
            return len(pms.data) > 0
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def get_charge_customer(self, external_charge_id: str) -> str | None:
        try:
            charge = await stripe.Charge.retrieve_async(
                external_charge_id, api_key=self._api_key
            )
            customer = charge.customer
            if customer is None:
                return None
            return customer if isinstance(customer, str) else customer.id
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    async def get_customer_portal_url(
        self, external_customer_id: str, return_url: str
    ) -> CustomerPortalResult:
        try:
            session = await stripe.billing_portal.Session.create_async(
                customer=external_customer_id,
                return_url=return_url,
                api_key=self._api_key,
            )
            return CustomerPortalResult(portal_url=session.url)
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

    def construct_webhook_event(
        self, payload: bytes, sig_header: str
    ) -> WebhookPayload:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self._webhook_secret
            )
        except stripe.SignatureVerificationError as exc:
            raise BillingWebhookException("Invalid webhook signature") from exc
        except stripe.StripeError as exc:
            raise BillingProviderException(str(exc)) from exc

        return WebhookPayload(
            external_event_id=event.id,
            event_type=event.type,
            raw=event.to_dict(),
        )

    @staticmethod
    def _map_subscription(sub: stripe.Subscription) -> ExternalSubscription:
        item = sub.items.data[0] if (sub.items and sub.items.data) else None

        canceled_at: datetime | None = None
        if sub.canceled_at:
            canceled_at = _ts_to_dt(sub.canceled_at)

        return ExternalSubscription(
            external_subscription_id=sub.id,
            external_customer_id=str(sub.customer)
            if isinstance(sub.customer, str)
            else sub.customer.id,
            status=sub.status,
            current_period_start=_ts_to_dt(item.current_period_start if item else None),
            current_period_end=_ts_to_dt(item.current_period_end if item else None),
            cancel_at_period_end=sub.cancel_at_period_end,
            canceled_at=canceled_at,
            external_price_id=item.price.id if item else None,
            cancel_at=_ts_to_dt(sub.cancel_at),
            trial_end=_ts_to_dt(sub.trial_end),
        )
