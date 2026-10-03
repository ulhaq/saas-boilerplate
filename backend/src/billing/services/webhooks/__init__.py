import logging
from typing import Annotated

from fastapi import Depends

from src.billing.enums import BillingAuditAction
from src.billing.exceptions import BillingProviderException
from src.billing.provider.dependencies import BillingProviderDep
from src.billing.repositories.manager import BillingRepositoryManager
from src.billing.services.base import BillingBaseService
from src.billing.services.webhooks.base import (
    WebhookHandler,
    WebhookHandlerGroup,
)
from src.billing.services.webhooks.catalog import CatalogWebhookHandlers
from src.billing.services.webhooks.checkout import CheckoutWebhookHandlers
from src.billing.services.webhooks.customers import CustomerWebhookHandlers
from src.billing.services.webhooks.invoices import InvoiceWebhookHandlers
from src.billing.services.webhooks.subscriptions import (
    SubscriptionWebhookHandlers,
)
from src.billing.telemetry import record_webhook_event

log = logging.getLogger(__name__)

HANDLER_GROUPS: tuple[type[WebhookHandlerGroup], ...] = (
    CheckoutWebhookHandlers,
    SubscriptionWebhookHandlers,
    InvoiceWebhookHandlers,
    CustomerWebhookHandlers,
    CatalogWebhookHandlers,
)


class WebhookService(BillingBaseService):
    def __init__(
        self,
        repos: Annotated[BillingRepositoryManager, Depends()],
        provider: BillingProviderDep,
    ) -> None:
        self.provider = provider
        super().__init__(repos)
        self._handlers: dict[str, WebhookHandler] = {}
        for group in HANDLER_GROUPS:
            self._handlers.update(group(repos, provider).handlers())

    async def process_webhook(self, payload: bytes, sig_header: str) -> bool:
        webhook = self.provider.construct_webhook_event(payload, sig_header)

        log.debug("Webhook!: %s", webhook)

        (
            event_record,
            should_process,
        ) = await self.repos.webhook_event.get_or_create_received(
            webhook.external_event_id,
            webhook.event_type,
        )

        if not should_process or event_record is None:
            record_webhook_event(webhook.event_type, "duplicate")
            return True

        try:
            await self._dispatch(webhook.event_type, webhook.raw)
        except BillingProviderException as exc:
            # Transient provider error - let Stripe retry
            await self.repos.webhook_event.mark_failed(event_record, str(exc))
            record_webhook_event(webhook.event_type, "retry")
            return False
        except Exception as exc:
            # Permanent error (bug, unexpected data)
            # log and ack to stop infinite retries
            log.error(
                "Permanent webhook handler failure [event_id=%s event_type=%s]: %s",
                webhook.external_event_id,
                webhook.event_type,
                exc,
                exc_info=True,
            )
            await self.repos.webhook_event.mark_failed(
                event_record, f"permanent: {exc}"
            )
            record_webhook_event(webhook.event_type, "failed")
            return True

        await self.repos.webhook_event.mark_processed(event_record)
        record_webhook_event(webhook.event_type, "processed")
        await self.log_audit(
            BillingAuditAction.BILLING_WEBHOOK,
            # Resolved after the handler ran: a first checkout's handler is what
            # links the Stripe customer to the organization.
            organization_id=await self._organization_id_for(webhook.raw),
            resource_type="webhook_event",
            details={
                "event_type": webhook.event_type,
                "stripe_event_id": webhook.external_event_id,
            },
        )
        return True

    async def _organization_id_for(self, raw: dict) -> int | None:
        """The organization an event concerns, via its Stripe customer; None for
        catalog events (products, prices) and customers no organization has."""
        obj = raw.get("data", {}).get("object", {})
        customer = (
            obj.get("id") if obj.get("object") == "customer" else obj.get("customer")
        )
        if not isinstance(customer, str):
            return None
        account = await self.repos.billing_account.get_by_external_customer_id(customer)
        return account.organization_id if account else None

    async def _dispatch(self, event_type: str, raw: dict) -> None:
        handler = self._handlers.get(event_type)
        if handler:
            await handler(raw)
