from abc import ABC, abstractmethod
from typing import Literal

from src.platform.billing.types import (
    CheckoutResult,
    CustomerPortalResult,
    ExternalPrice,
    ExternalProduct,
    ExternalSubscription,
    WebhookPayload,
)


class BillingProviderABC(ABC):
    @abstractmethod
    async def search_product_by_name(self, name: str) -> ExternalProduct | None: ...

    @abstractmethod
    async def create_product(
        self, name: str, description: str | None
    ) -> ExternalProduct: ...

    @abstractmethod
    async def update_product(
        self, external_product_id: str, name: str, description: str | None
    ) -> ExternalProduct: ...

    @abstractmethod
    async def archive_product(self, external_product_id: str) -> None: ...

    @abstractmethod
    async def reactivate_product(self, external_product_id: str) -> None: ...

    @abstractmethod
    async def create_price(
        self,
        external_product_id: str,
        amount: int,
        currency: str,
        interval: Literal["day", "month", "week", "year"],
        interval_count: int,
        tax_behavior: Literal["exclusive", "inclusive", "unspecified"] = "exclusive",
    ) -> ExternalPrice: ...

    @abstractmethod
    async def archive_price(self, external_price_id: str) -> None: ...

    @abstractmethod
    async def get_or_create_customer(
        self, organization_id: int, organization_name: str, email: str | None = None
    ) -> str: ...

    @abstractmethod
    async def update_customer(
        self,
        external_customer_id: str,
        email: str | None = None,
        name: str | None = None,
    ) -> None: ...

    @abstractmethod
    async def create_checkout_session(
        self,
        external_customer_id: str | None,
        external_price_id: str,
        amount: int,
        success_url: str,
        cancel_url: str,
        metadata: dict,
        trial_period_days: int | None = None,
    ) -> CheckoutResult: ...

    @abstractmethod
    async def cancel_subscription(
        self, external_subscription_id: str
    ) -> ExternalSubscription: ...

    @abstractmethod
    async def delete_subscription(self, external_subscription_id: str) -> None: ...

    @abstractmethod
    async def resume_subscription(
        self, external_subscription_id: str
    ) -> ExternalSubscription: ...

    @abstractmethod
    async def switch_subscription_price(
        self,
        external_subscription_id: str,
        new_external_price_id: str,
        skip_proration: bool = False,
        new_amount: int = 0,
    ) -> ExternalSubscription: ...

    @abstractmethod
    async def get_customer_portal_url(
        self, external_customer_id: str, return_url: str
    ) -> CustomerPortalResult: ...

    @abstractmethod
    async def create_subscription(
        self,
        external_customer_id: str,
        external_price_id: str,
        trial_period_days: int | None = None,
    ) -> ExternalSubscription: ...

    @abstractmethod
    async def has_payment_method(self, external_customer_id: str) -> bool: ...

    @abstractmethod
    async def get_charge_customer(self, external_charge_id: str) -> str | None:
        """Return the external customer id the charge belongs to, if any."""

    @abstractmethod
    def construct_webhook_event(
        self, payload: bytes, sig_header: str
    ) -> WebhookPayload:
        """
        Parse and verify a raw webhook payload.
        Raises BillingWebhookException on invalid signature.
        """
