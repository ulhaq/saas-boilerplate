import logging
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from src.billing.services.common import _get_period_field, _ts
from src.billing.services.webhooks.base import (
    WebhookHandler,
    WebhookHandlerGroup,
)
from src.platform.core.config import settings

log = logging.getLogger(__name__)


class SubscriptionWebhookHandlers(WebhookHandlerGroup):
    def handlers(self) -> dict[str, WebhookHandler]:
        return {
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "customer.subscription.trial_will_end": (
                self._handle_subscription_trial_will_end
            ),
            "customer.subscription.paused": self._handle_subscription_paused,
            "customer.subscription.resumed": self._handle_subscription_resumed,
        }

    async def _handle_subscription_created(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        sub_id: str = obj["id"]

        account = None
        sub = await self.repos.subscription.get_by_external_subscription_id_locked(
            sub_id
        )
        if not sub:
            # subscription.created fires before checkout.session.completed so
            # external_subscription_id is not yet set - fall back to customer lookup.
            customer_id: str | None = obj.get("customer")
            if customer_id:
                account = (
                    await self.repos.billing_account.get_by_external_customer_id_locked(
                        customer_id
                    )
                )
                if account:
                    sub = await self.repos.subscription.get_active_for_organization_locked(  # noqa: E501
                        account.organization_id
                    )
                    if sub and self._tracks_another_subscription(sub, sub_id):
                        await self._cancel_duplicate_subscription(
                            account.organization_id, sub_id
                        )
                        return
                    if not sub:
                        # Edge case: no active subscription exists (e.g. free plan
                        # seed failed at registration). Create one now so the
                        # Stripe subscription is tracked locally.
                        sub = await self.repos.subscription.create_or_get_active(
                            organization_id=account.organization_id,
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
            if account is None:
                account = (
                    await self.repos.billing_account.get_by_external_customer_id_locked(
                        obj.get("customer", "")
                    )
                )
            if account and not account.trial_used:
                await self.repos.billing_account.update(account, trial_used=True)

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

        account = await self.repos.billing_account.get_for_organization(
            sub.organization_id
        )
        has_payment_method = account.has_payment_method if account else False

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
