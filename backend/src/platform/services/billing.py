import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import Depends

from src.platform.billing.dependencies import BillingProviderDep
from src.platform.core.config import settings
from src.platform.core.dependencies import authenticate
from src.platform.core.exceptions import (
    AlreadyExistsException,
    BillingProviderException,
    NotFoundException,
    ValidationException,
)
from src.platform.core.hooks import HookEvent, emit
from src.platform.core.security import Auth
from src.platform.enums import AuditAction, ErrorCode, Permission
from src.platform.models.billing import PlanPrice, Subscription
from src.platform.models.organization import Organization
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.billing import (
    CheckoutIn,
    CheckoutOut,
    CustomerPortalOut,
    PlanOut,
    PlanSettingOut,
    StartTrialIn,
    SubscriptionOut,
    SwitchPlanIn,
    UpdateBillingEmailIn,
    UsageItemOut,
    UsageOut,
)
from src.platform.services.base import BaseService
from src.platform.services.email_content import format_date
from src.platform.services.mailer import send_email

log = logging.getLogger(__name__)


def _ts(ts: int | None) -> datetime | None:
    return datetime.fromtimestamp(ts, tz=UTC) if ts else None


async def notify_subscription_managers(
    organization: Organization,
    email_template: str,
    data: dict,
) -> int:
    """Email every member of ``organization`` who can manage the subscription.

    Returns the number of recipients. Used both by webhook handlers and by the
    trial reminder loop, so it takes an Organization rather than reading one
    through a request-scoped service.
    """
    sent = 0
    for user in organization.users:
        if not any(
            p.name == Permission.MANAGE_SUBSCRIPTION
            for role in user.roles
            for p in role.permissions
        ):
            continue
        # Render any date in the recipient's locale; everything else passes
        # through. Subject is derived per recipient locale inside send_email.
        localized_data = {
            key: format_date(value, user.locale) if isinstance(value, date) else value
            for key, value in data.items()
        }
        await asyncio.to_thread(
            send_email,
            address=user.email,
            user_name=user.name,
            email_template=email_template,
            locale=user.locale,
            data=localized_data,
        )
        sent += 1
    return sent


def _get_period_field(obj: dict, field: str) -> int | None:
    """
    Extract a period timestamp field, falling back to the first subscription item.
    """
    val = obj.get(field)
    if val:
        return val
    items = obj.get("items", {}).get("data", [])
    return items[0].get(field) if items else None


def _is_active_free_sub(sub: Subscription | None) -> bool:
    return (
        sub is not None
        and sub.status == "active"
        and sub.plan_price is not None
        and sub.plan_price.amount == 0
    )


class PlanService(BaseService):
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        provider: BillingProviderDep,
    ) -> None:
        self.provider = provider
        super().__init__(repos)

    async def get_plan(self, plan_id: int) -> PlanOut:
        plan = await self.repos.plan.get(plan_id)
        if not plan:
            raise NotFoundException(f"Plan not found. [plan_id={plan_id}]")
        return PlanOut.model_validate(plan)

    async def get_all_plans(self) -> list[PlanOut]:
        plans = await self.repos.plan.get_active_plans()
        return [PlanOut.model_validate(p) for p in plans]


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

    async def start_checkout(self, schema_in: CheckoutIn) -> CheckoutOut:
        price = await self.repos.plan_price.get(schema_in.plan_price_id)
        if not price or not price.is_active:
            raise NotFoundException(
                f"Plan price not found or inactive. [id={schema_in.plan_price_id}]"
            )
        if not price.external_price_id:
            raise NotFoundException("Plan price is not synced with billing provider.")

        existing = await self.repos.subscription.get_active_for_organization_locked(
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

        # Get or create provider customer
        organization = await self.repos.organization.get(
            self.current_user.organization_id
        )
        if not organization:
            raise NotFoundException("Organization not found.")

        # Acquire a transaction-scoped advisory lock keyed on organization_id to prevent
        # two concurrent first-time checkouts from creating duplicate Stripe customers.
        # The lock is automatically released when the transaction commits or rolls back.
        await self._acquire_checkout_lock(self.current_user.organization_id)

        # Re-check after acquiring the lock - a concurrent request may have inserted a
        # subscription row between our initial check and the lock acquisition.
        existing = await self.repos.subscription.get_active_for_organization_locked(
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
            external_price_id=price.external_price_id,
            amount=price.amount,
            success_url=settings.billing_success_url,
            cancel_url=settings.billing_cancel_url,
            metadata=metadata,
            trial_period_days=None,
        )

        # Do not touch the local subscription row here. The row is created or
        # updated by _handle_subscription_created once Stripe confirms the
        # subscription exists. This keeps start_checkout() a pure session
        # factory: it creates a Stripe checkout session and nothing else.
        # _handle_checkout_session_expired handles cleanup if checkout is
        # abandoned; since no row is changed here, that handler is a no-op for
        # free-plan users (status stays "active", not "incomplete").

        await self.log_audit(
            AuditAction.BILLING_CHECKOUT_START,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="subscription",
            details={"plan_price_id": schema_in.plan_price_id},
        )
        return CheckoutOut(checkout_url=result.checkout_url)

    async def start_trial(self, schema_in: StartTrialIn) -> CheckoutOut:
        price = await self.repos.plan_price.get(schema_in.plan_price_id)
        if not price or not price.is_active:
            raise NotFoundException(
                f"Plan price not found or inactive. [id={schema_in.plan_price_id}]"
            )
        if price.amount == 0:
            raise ValidationException("Cannot start a trial on the free plan.")
        if not price.external_price_id:
            raise NotFoundException("Plan price is not synced with billing provider.")

        if not settings.billing_trial_period_days:
            raise ValidationException("Trials are not configured.")

        organization = await self.repos.organization.get(
            self.current_user.organization_id
        )
        if not organization:
            raise NotFoundException("Organization not found.")

        if organization.trial_used:
            raise ValidationException(
                "Trial has already been used.",
                error_code=ErrorCode.TRIAL_ALREADY_USED,
            )

        # Acquire lock to prevent concurrent trial
        # starts from creating duplicate customers.
        await self._acquire_checkout_lock(self.current_user.organization_id)

        # Re-check after acquiring the lock.
        organization = await self.repos.organization.get(
            self.current_user.organization_id
        )
        if not organization or organization.trial_used:
            raise ValidationException(
                "Trial has already been used.",
                error_code=ErrorCode.TRIAL_ALREADY_USED,
            )

        existing = await self.repos.subscription.get_active_for_organization_locked(
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
            external_price_id=price.external_price_id,
            amount=price.amount,
            success_url=settings.billing_success_url,
            cancel_url=settings.billing_cancel_url,
            metadata=metadata,
            trial_period_days=settings.billing_trial_period_days,
        )
        await self.log_audit(
            AuditAction.BILLING_TRIAL_START,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="subscription",
            details={"plan_price_id": schema_in.plan_price_id},
        )
        return CheckoutOut(checkout_url=result.checkout_url)

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

        price = await self.repos.plan_price.get(schema_in.plan_price_id)
        if not price or not price.is_active:
            raise NotFoundException(
                f"Plan price not found or inactive. [id={schema_in.plan_price_id}]"
            )
        if price.amount == 0:
            raise ValidationException(
                "Cannot switch to the free plan. "
                "Cancel your subscription to return to the free tier."
            )
        if not price.external_price_id:
            raise NotFoundException("Plan price is not synced with billing provider.")

        if sub.plan_price_id == price.id:
            raise ValidationException("Subscription is already on this plan.")

        old_plan_price_id = sub.plan_price_id
        ext_sub = await self.provider.switch_subscription_price(
            sub.external_subscription_id,
            price.external_price_id,
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

    async def _acquire_checkout_lock(self, organization_id: int) -> None:
        await self.repos.subscription.acquire_checkout_lock(organization_id)

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


class WebhookService(BaseService):
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        provider: BillingProviderDep,
    ) -> None:
        self.provider = provider
        super().__init__(repos)

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
            return True

        try:
            await self._dispatch(webhook.event_type, webhook.raw)
        except BillingProviderException as exc:
            # Transient provider error - let Stripe retry
            await self.repos.webhook_event.mark_failed(event_record, str(exc))
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
            return True

        await self.repos.webhook_event.mark_processed(event_record)
        await self.log_audit(
            AuditAction.BILLING_WEBHOOK,
            resource_type="webhook_event",
            details={
                "event_type": webhook.event_type,
                "stripe_event_id": webhook.external_event_id,
            },
        )
        return True

    async def _dispatch(self, event_type: str, raw: dict) -> None:
        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "checkout.session.expired": self._handle_checkout_session_expired,
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "customer.subscription.trial_will_end": (
                self._handle_subscription_trial_will_end
            ),
            "customer.subscription.paused": self._handle_subscription_paused,
            "customer.subscription.resumed": self._handle_subscription_resumed,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            "invoice.payment_succeeded": self._handle_invoice_payment_succeeded,
            "invoice.payment_action_required": (
                self._handle_invoice_payment_action_required
            ),
            "invoice.marked_uncollectible": self._handle_invoice_marked_uncollectible,
            "charge.dispute.created": self._handle_charge_dispute_created,
            "customer.updated": self._handle_customer_updated,
            "payment_method.attached": self._handle_payment_method_attached,
            "payment_method.detached": self._handle_payment_method_detached,
            "product.created": self._handle_product_created,
            "product.updated": self._handle_product_updated,
            "price.created": self._handle_price_created,
            "price.updated": self._handle_price_updated,
        }
        handler = handlers.get(event_type)
        if handler:
            await handler(raw)

    async def _get_organization_from_checkout_event(
        self, obj: dict
    ) -> Organization | None:
        customer_id: str | None = obj.get("customer")
        metadata: dict = obj.get("metadata", {})

        organization = None
        if customer_id:
            organization = (
                await self.repos.organization.get_by_external_customer_id_locked(
                    customer_id
                )
            )
        if not organization:
            organization_id_str = metadata.get("organization_id")
            if organization_id_str:
                try:
                    organization = await self.repos.organization.get(
                        int(organization_id_str)
                    )
                except ValueError:
                    log.warning(
                        "Invalid organization_id in checkout metadata [value=%r]",
                        organization_id_str,
                    )
        return organization

    async def _notify_subscription_managers(
        self,
        organization_id: int,
        email_template: str,
        data: dict,
    ) -> None:
        organization = await self.repos.organization.get(organization_id)
        if not organization:
            return
        await notify_subscription_managers(organization, email_template, data)

    async def _notify_payment_failed(self, sub: Subscription) -> None:
        await self._notify_subscription_managers(
            sub.organization_id,
            "payment-failed",
            {"billing_url": f"{settings.frontend_url}/settings/billing"},
        )

    async def _notify_payment_uncollectible(self, sub: Subscription) -> None:
        await self._notify_subscription_managers(
            sub.organization_id,
            "payment-uncollectible",
            {"billing_url": f"{settings.frontend_url}/settings/billing"},
        )

    async def _handle_checkout_completed(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        subscription_id: str | None = obj.get("subscription")
        metadata: dict = obj.get("metadata", {})

        customer_id: str | None = obj.get("customer")
        if not subscription_id or not customer_id:
            return

        # Try to find existing subscription row by customer or metadata organization_id
        organization = await self._get_organization_from_checkout_event(obj)
        if not organization:
            return

        # If we fell back to the metadata lookup the organization
        # has no external_customer_id yet.
        # Stamp it now so future webhook events can
        # find the organization by customer ID.
        if not organization.external_customer_id:
            await self.repos.organization.update(
                organization, external_customer_id=customer_id
            )

        sub = await self.repos.subscription.get_active_for_organization_locked(
            organization.id
        )
        if not sub:
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

    async def _handle_subscription_updated(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        sub_id: str = obj["id"]

        sub = await self.repos.subscription.get_by_external_subscription_id_locked(
            sub_id
        )
        if not sub:
            return

        new_status: str = obj.get("status", sub.status)
        if new_status in ("unpaid", "incomplete_expired"):
            # Terminal payment states: unpaid means Stripe exhausted dunning
            # without collecting; incomplete_expired means the initial payment
            # never completed. Both end paid access - downgrade to free like
            # the invoice.marked_uncollectible path, instead of persisting a
            # status that entitlement queries would treat as no subscription.
            # An incomplete_expired subscription is already terminal on
            # Stripe's side and cannot be canceled via the API.
            await self._downgrade_to_free(sub, cancel_remote=new_status == "unpaid")
            if new_status == "unpaid":
                await self._notify_payment_uncollectible(sub)
            return

        updates: dict = {
            "status": new_status,
            "current_period_start": _ts(_get_period_field(obj, "current_period_start")),
            "current_period_end": _ts(_get_period_field(obj, "current_period_end")),
            "canceled_at": _ts(obj.get("canceled_at")),
            "cancel_at": _ts(obj.get("cancel_at")),
            "trial_end": _ts(obj.get("trial_end")),
        }
        # Only update cancel_at_period_end when explicitly present in the event
        # defaulting to False would silently un-schedule pending cancellations.
        if "cancel_at_period_end" in obj:
            updates["cancel_at_period_end"] = obj["cancel_at_period_end"]

        # Check if price changed (e.g. plan upgrade via portal)
        items = obj.get("items", {}).get("data", [])
        if items:
            new_price_id: str | None = (items[0].get("price") or {}).get("id")
            if (
                new_price_id
                and sub.plan_price
                and sub.plan_price.external_price_id != new_price_id
            ):
                new_price = await self.repos.plan_price.get_by_external_price_id(
                    new_price_id
                )
                if new_price:
                    updates["plan_price_id"] = new_price.id

        # Only notify domain modules when plan-relevant state actually changed.
        # Stripe also fires subscription.updated for metadata/tax/billing-anchor
        # changes, and every PLAN_CHANGED emission triggers a reconciliation
        # run with side effects (e.g. pausing watches over the plan limit).
        plan_state_changed = new_status != sub.status or "plan_price_id" in updates
        await self.repos.subscription.update(sub, **updates)
        if plan_state_changed:
            await self._plan_changed(sub.organization_id)

    async def _handle_subscription_deleted(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        sub_id: str = obj["id"]

        sub = await self.repos.subscription.get_by_external_subscription_id_locked(
            sub_id
        )
        if not sub:
            log.debug(
                "subscription.deleted: no local subscription found [stripe_sub_id=%s]",
                sub_id,
            )
            return

        # Restore to free plan in-place. Updating the existing row (rather than
        # cancel + new row) avoids a unique-constraint conflict - only one
        # non-canceled subscription per organization is allowed. If no free plan is
        # configured, fall back to marking the row as canceled.
        free_price = await self.repos.plan_price.get_free_price()
        if free_price:
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
        else:
            canceled_at_ts = obj.get("canceled_at")
            updates: dict = {"status": "canceled"}
            if canceled_at_ts:
                updates["canceled_at"] = datetime.fromtimestamp(canceled_at_ts, tz=UTC)
            elif not sub.canceled_at:
                # Stripe omitted the timestamp - fall back to now rather than nulling it
                updates["canceled_at"] = datetime.now(UTC)
            await self.repos.subscription.update(sub, **updates)
        await self._plan_changed(sub.organization_id)

    async def _plan_changed(self, organization_id: int) -> None:
        """Notify domain modules (via hooks) that the org's plan state changed,
        so they can reconcile plan-limited resources."""
        await emit(
            HookEvent.PLAN_CHANGED, repos=self.repos, organization_id=organization_id
        )

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

    async def _get_subscription_from_invoice(self, obj: dict) -> Subscription | None:
        parent = obj.get("parent") or {}
        sub_details = parent.get("subscription_details") or {}
        sub_id: str | None = sub_details.get("subscription") or obj.get("subscription")
        if sub_id:
            return await self.repos.subscription.get_by_external_subscription_id_locked(
                sub_id
            )
        customer_id: str | None = obj.get("customer")
        if customer_id:
            organization = (
                await self.repos.organization.get_by_external_customer_id_locked(
                    customer_id
                )
            )
            if organization:
                return await self.repos.subscription.get_active_for_organization_locked(
                    organization.id
                )
        return None

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

    async def _handle_subscription_created(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        sub_id: str = obj["id"]

        organization = None
        sub = await self.repos.subscription.get_by_external_subscription_id_locked(
            sub_id
        )
        if not sub:
            # subscription.created fires before checkout.session.completed so
            # external_subscription_id is not yet set - fall back to customer lookup.
            customer_id: str | None = obj.get("customer")
            if customer_id:
                organization = (
                    await self.repos.organization.get_by_external_customer_id_locked(
                        customer_id
                    )
                )
                if organization:
                    sub = await self.repos.subscription.get_active_for_organization_locked(  # noqa: E501
                        organization.id
                    )
                    if not sub:
                        # Edge case: no active subscription exists (e.g. free plan
                        # seed failed at registration). Create one now so the
                        # Stripe subscription is tracked locally.
                        sub = await self.repos.subscription.create_or_get_active(
                            organization_id=organization.id,
                            plan_price_id=None,
                            status="incomplete",
                        )
        if not sub:
            return

        updates: dict = {
            "external_subscription_id": sub_id,
            "status": obj.get("status", sub.status),
            "cancel_at_period_end": obj.get("cancel_at_period_end", False),
            "current_period_start": _ts(_get_period_field(obj, "current_period_start")),
            "current_period_end": _ts(_get_period_field(obj, "current_period_end")),
            "canceled_at": _ts(obj.get("canceled_at")),
            "cancel_at": _ts(obj.get("cancel_at")),
        }
        if obj.get("trial_end"):
            updates["trial_end"] = _ts(obj["trial_end"])

        items = obj.get("items", {}).get("data", [])
        if items:
            new_price_id: str | None = (items[0].get("price") or {}).get("id")
            if new_price_id:
                new_price = await self.repos.plan_price.get_by_external_price_id(
                    new_price_id
                )
                if new_price:
                    updates["plan_price_id"] = new_price.id

        await self.repos.subscription.update(sub, **updates)
        await self._plan_changed(sub.organization_id)

        if updates.get("status") == "trialing":
            if organization is None:
                organization = (
                    await self.repos.organization.get_by_external_customer_id_locked(
                        obj.get("customer", "")
                    )
                )
            if organization and not organization.trial_used:
                await self.repos.organization.update(organization, trial_used=True)

    async def _handle_checkout_session_expired(self, raw: dict) -> None:
        obj = raw["data"]["object"]

        organization = await self._get_organization_from_checkout_event(obj)
        sub = None
        if organization:
            sub = await self.repos.subscription.get_active_for_organization_locked(
                organization.id
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

    async def _downgrade_to_free(
        self, sub: Subscription, *, cancel_remote: bool = True
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
                sub, status="canceled", canceled_at=datetime.now(UTC)
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
        organization = await self.repos.organization.get_by_external_customer_id_locked(
            customer_id
        )
        if not organization:
            return
        sub = await self.repos.subscription.get_active_for_organization_locked(
            organization.id
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

    async def _handle_subscription_trial_will_end(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        sub_id: str = obj["id"]
        trial_end_ts: int | None = obj.get("trial_end")

        sub = await self.repos.subscription.get_by_external_subscription_id_locked(
            sub_id
        )
        if not sub:
            return

        if trial_end_ts:
            await self.repos.subscription.update(
                sub,
                trial_end=datetime.fromtimestamp(trial_end_ts, tz=UTC),
            )

        # Pass a date object; _notify_subscription_managers renders it in each
        # recipient's locale. The calendar day is taken in the display timezone.
        trial_end_date: date | str = (
            datetime.fromtimestamp(
                trial_end_ts, tz=ZoneInfo(settings.display_timezone)
            ).date()
            if trial_end_ts
            else "soon"
        )

        organization = await self.repos.organization.get(sub.organization_id)
        has_payment_method = organization.has_payment_method if organization else False

        await self._notify_subscription_managers(
            sub.organization_id,
            "trial-ending",
            {
                "trial_end_date": trial_end_date,
                "billing_url": f"{settings.frontend_url}/settings/billing",
                "has_payment_method": has_payment_method,
            },
        )

    async def _handle_subscription_paused(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        sub_id: str = obj["id"]

        sub = await self.repos.subscription.get_by_external_subscription_id_locked(
            sub_id
        )
        if not sub:
            return

        # pause_collection is set for explicit manual pauses;
        # trial-end pauses leave it null
        is_trial_end_pause = not obj.get("pause_collection")

        if not is_trial_end_pause:
            await self.repos.subscription.update(sub, status="paused")
            await self._notify_subscription_managers(
                sub.organization_id,
                "subscription-paused",
                {"billing_url": f"{settings.frontend_url}/settings/billing"},
            )
            return

        # Trial ended without payment method - downgrade to free locally and
        # cancel the Stripe subscription. No need to resume first since we are
        # cancelling rather than modifying the subscription price.
        if not await self._downgrade_to_free(sub):
            return

        await self._notify_subscription_managers(
            sub.organization_id,
            "trial-ended",
            {"billing_url": f"{settings.frontend_url}/settings/billing"},
        )

    async def _handle_subscription_resumed(self, raw: dict) -> None:
        await self._handle_subscription_updated(raw)

        # Only email on genuine user-initiated resumes. When we resume internally
        # as part of the trial-end downgrade, pause_collection was already null
        # so it won't appear in previous_attributes. A manual resume always
        # transitions pause_collection from a set value to null.
        prev = raw["data"].get("previous_attributes", {})
        if "pause_collection" not in prev:
            return

        obj = raw["data"]["object"]
        sub_id: str = obj["id"]

        sub = await self.repos.subscription.get_by_external_subscription_id_locked(
            sub_id
        )
        if not sub:
            return

        await self._notify_subscription_managers(
            sub.organization_id,
            "subscription-resumed",
            {"billing_url": f"{settings.frontend_url}/settings/billing"},
        )

    async def _handle_product_created(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        external_product_id: str = obj["id"]

        plan = await self.repos.plan.get_by_external_product_id(external_product_id)
        if plan:
            return

        name: str = obj.get("name", external_product_id)
        unlinked = await self.repos.plan.get_unlinked_by_name(name)
        if unlinked:
            await self.repos.plan.update(
                unlinked, external_product_id=external_product_id
            )
            return

        await self.repos.plan.create(
            name=name,
            description=obj.get("description"),
            external_product_id=external_product_id,
        )

    async def _handle_product_updated(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        external_product_id: str = obj["id"]

        plan = await self.repos.plan.get_by_external_product_id(external_product_id)
        if not plan:
            return

        updates: dict = {}
        if "name" in obj:
            updates["name"] = obj["name"]
        if "description" in obj:
            updates["description"] = obj.get("description")
        if "active" in obj:
            updates["is_active"] = obj["active"]
        if updates:
            await self.repos.plan.update(plan, **updates)

    async def _handle_price_created(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        external_price_id: str = obj["id"]

        existing = await self.repos.plan_price.get_by_external_price_id(
            external_price_id
        )
        if existing:
            return

        external_product_id: str | None = obj.get("product")
        if not external_product_id:
            return

        plan = await self.repos.plan.get_by_external_product_id(external_product_id)
        if not plan:
            return

        recurring: dict = obj.get("recurring") or {}
        amount: int = obj.get("unit_amount", 0)
        currency: str = obj.get("currency", "dkk")
        interval: str = recurring.get("interval", "month")
        interval_count: int = recurring.get("interval_count", 1)

        unlinked = await self.repos.plan_price.get_unlinked_by_attributes(
            external_product_id=external_product_id,
            amount=amount,
            currency=currency,
            interval=interval,
            interval_count=interval_count,
        )
        if unlinked:
            await self.repos.plan_price.update(
                unlinked, external_price_id=external_price_id
            )
            return

        await self.repos.plan_price.create(
            plan_id=plan.id,
            amount=amount,
            currency=currency,
            interval=interval,
            interval_count=interval_count,
            external_price_id=external_price_id,
        )

    async def _handle_price_updated(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        external_price_id: str = obj["id"]

        price = await self.repos.plan_price.get_by_external_price_id(external_price_id)
        if not price:
            return

        if "active" in obj:
            await self.repos.plan_price.update(price, is_active=obj["active"])


class UsageService(BaseService):
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        self.current_user = current_user
        super().__init__(repos)

    async def get_current_usage(self) -> UsageOut:
        period_start = date.today().replace(day=1)
        limits = await self.repos.plan_setting.get_settings_for_organization(
            self.current_user.organization_id
        )
        records = await self.repos.plan_usage.get_for_organization(
            self.current_user.organization_id, period_start
        )
        count_by_metric = {r.metric: r.count for r in records}
        usage_items = [
            UsageItemOut(
                metric=limit.key,
                count=count_by_metric.get(limit.key, 0),
                limit=limit.value,
            )
            for limit in limits
        ]
        return UsageOut(period_start=period_start, usage=usage_items)


class BillingMaintenanceService(BaseService):
    def __init__(self, repos: Annotated[RepositoryManager, Depends()]) -> None:
        super().__init__(repos)

    async def cleanup_stale_checkouts(self, max_age_hours: int = 48) -> int:
        """
        Bulk-cancels stale incomplete subscriptions in a single UPDATE.

        Targets rows that have no external_subscription_id (checkout was never
        completed) and are older than max_age_hours. This handles the case where
        the checkout.session.expired webhook permanently failed and the row was
        never cleaned up by the normal event flow.

        Safe to call repeatedly - rows are only updated once (incomplete > canceled).
        Intended to be called from a scheduled job, e.g. daily with max_age_hours=48.
        """
        threshold = datetime.now(UTC) - timedelta(hours=max_age_hours)
        count = await self.repos.subscription.bulk_cancel_stale_incomplete(threshold)
        log.info("Marked %d stale incomplete subscription(s) as canceled", count)
        return count

    async def send_trial_reminders(self) -> int:
        """
        Emails organizations that still have an unused trial sitting on their
        account, once the signup has had time to settle.

        Targets organizations created more than ``billing_trial_reminder_delay_days``
        ago that never started their trial and are not blocked from starting one.
        Each organization is stamped with ``trial_reminder_sent_at`` after its
        managers are emailed, so the reminder goes out exactly once - a crash
        mid-batch rolls back the whole transaction and the batch is retried on
        the next tick.
        """
        if not settings.billing_trial_period_days:
            return 0

        created_before = datetime.now(UTC) - timedelta(
            days=settings.billing_trial_reminder_delay_days
        )
        organizations = await self.repos.organization.get_trial_reminder_candidates(
            created_before
        )

        reminded = 0
        for organization in organizations:
            recipients = await notify_subscription_managers(
                organization,
                "trial-available",
                {
                    "trial_days": settings.billing_trial_period_days,
                    "billing_url": f"{settings.frontend_url}/settings/billing",
                },
            )
            # Stamp regardless of recipient count: an organization with no
            # subscription manager has nobody to remind, and leaving it unstamped
            # would re-scan it on every tick forever.
            await self.repos.organization.update(
                organization, trial_reminder_sent_at=datetime.now(UTC)
            )
            if recipients:
                reminded += 1
        return reminded


async def run_trial_reminder_loop(session_factory: Any) -> None:
    """
    Background loop that sends the "your trial is still available" reminder.

    Runs once every ``billing_trial_reminder_interval_seconds`` (daily by
    default). Must run in the worker process only - running it in the API would
    email each organization once per API replica.
    """
    while True:
        try:
            async with session_factory() as session:
                async with session.begin():
                    service = BillingMaintenanceService(RepositoryManager(session))
                    count = await service.send_trial_reminders()
                    log.info("Trial reminder: %d organization(s) emailed", count)
        except Exception as exc:
            log.error("Trial reminder loop error: %s", exc, exc_info=True)
        await asyncio.sleep(settings.billing_trial_reminder_interval_seconds)


async def run_stale_checkout_cleanup_loop(session_factory: Any) -> None:
    """
    Background loop that calls cleanup_stale_checkouts once every 24 hours.
    Intended to be launched as an asyncio task from the application lifespan.
    """
    while True:
        try:
            async with session_factory() as session:
                async with session.begin():
                    service = BillingMaintenanceService(RepositoryManager(session))
                    count = await service.cleanup_stale_checkouts()
                    log.info(
                        "Stale checkout cleanup: %d subscription(s) canceled",
                        count,
                    )
        except Exception as exc:
            log.error("Stale checkout cleanup loop error: %s", exc, exc_info=True)
        await asyncio.sleep(settings.billing_cleanup_interval_seconds)
