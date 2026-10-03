import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends

from src.billing.config import billing_settings
from src.billing.provider.abc import BillingProviderABC
from src.billing.provider.dependencies import get_billing_provider
from src.billing.repositories.manager import BillingRepositoryManager
from src.billing.services.base import BillingBaseService
from src.billing.services.common import notify_subscription_managers
from src.platform.core.config import settings
from src.platform.core.database import try_job_lock
from src.platform.core.telemetry import track_worker_run

log = logging.getLogger(__name__)


class BillingMaintenanceService(BillingBaseService):
    def __init__(self, repos: Annotated[BillingRepositoryManager, Depends()]) -> None:
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
        if not billing_settings.billing_trial_period_days:
            return 0

        created_before = datetime.now(UTC) - timedelta(
            days=billing_settings.billing_trial_reminder_delay_days
        )
        accounts = await self.repos.billing_account.get_trial_reminder_candidates(
            created_before
        )

        reminded = 0
        for account in accounts:
            recipients = await notify_subscription_managers(
                self.repos,
                account.organization,
                "trial-available",
                {
                    "trial_days": billing_settings.billing_trial_period_days,
                    "billing_url": f"{settings.frontend_url}/settings/billing",
                },
            )
            # Stamp regardless of recipient count: an organization with no
            # subscription manager has nobody to remind, and leaving it unstamped
            # would re-scan it on every tick forever.
            await self.repos.billing_account.update(
                account, trial_reminder_sent_at=datetime.now(UTC)
            )
            if recipients:
                reminded += 1
        return reminded


async def sync_customer_emails(
    repos: BillingRepositoryManager, provider: BillingProviderABC
) -> int:
    """Push pending customer emails (`BillingAccount.pending_customer_email`)
    to the provider. A failed push stays pending and is retried on the next
    tick; a push is only marked done if no newer email replaced it meanwhile.
    Returns how many were synced."""
    synced = 0
    for account in await repos.billing_account.get_pending_customer_syncs():
        email = account.pending_customer_email
        customer_id = account.external_customer_id
        if email is None or customer_id is None:
            continue
        try:
            await provider.update_customer(customer_id, email=email)
        except Exception as exc:
            log.warning(
                "Customer sync failed, will retry [customer=%s]: %s", customer_id, exc
            )
            continue
        if await repos.billing_account.clear_pending_customer_email(account.id, email):
            synced += 1
    return synced


async def run_customer_sync_loop(session_factory: Any) -> None:
    """
    Background loop that pushes pending customer emails to the provider, every
    ``billing_customer_sync_interval_seconds``. Changes are recorded where they
    happen (an ownership transfer) and synced here, outside any request, so a
    provider outage delays the update instead of failing the change.
    """
    interval = billing_settings.billing_customer_sync_interval_seconds
    while True:
        try:
            with track_worker_run("customer_sync", interval):
                async with session_factory() as session:
                    async with session.begin():
                        if await try_job_lock(session, "customer_sync"):
                            count = await sync_customer_emails(
                                BillingRepositoryManager(session),
                                get_billing_provider(),
                            )
                            if count:
                                log.info("Customer sync: %d customer(s)", count)
        except Exception as exc:
            log.error("Customer sync loop error: %s", exc, exc_info=True)
        await asyncio.sleep(interval)


async def run_trial_reminder_loop(session_factory: Any) -> None:
    """
    Background loop that sends the "your trial is still available" reminder.

    Runs once every ``billing_trial_reminder_interval_seconds`` (daily by
    default). Must run in the worker process only - running it in the API would
    email each organization once per API replica.
    """
    interval = billing_settings.billing_trial_reminder_interval_seconds
    while True:
        try:
            with track_worker_run("trial_reminder", interval):
                async with session_factory() as session:
                    async with session.begin():
                        if await try_job_lock(session, "trial_reminder"):
                            service = BillingMaintenanceService(
                                BillingRepositoryManager(session)
                            )
                            count = await service.send_trial_reminders()
                            log.info(
                                "Trial reminder: %d organization(s) emailed", count
                            )
                        else:
                            log.info("Trial reminder: running in another worker")
        except Exception as exc:
            log.error("Trial reminder loop error: %s", exc, exc_info=True)
        await asyncio.sleep(interval)


async def run_stale_checkout_cleanup_loop(session_factory: Any) -> None:
    """
    Background loop that calls cleanup_stale_checkouts once every 24 hours.
    Intended to be launched as an asyncio task from the application lifespan.
    """
    interval = billing_settings.billing_cleanup_interval_seconds
    while True:
        try:
            with track_worker_run("stale_checkout_cleanup", interval):
                async with session_factory() as session:
                    async with session.begin():
                        if await try_job_lock(session, "stale_checkout_cleanup"):
                            service = BillingMaintenanceService(
                                BillingRepositoryManager(session)
                            )
                            count = await service.cleanup_stale_checkouts()
                            log.info(
                                "Stale checkout cleanup: %d subscription(s) canceled",
                                count,
                            )
                        else:
                            log.info(
                                "Stale checkout cleanup: running in another worker"
                            )
        except Exception as exc:
            log.error("Stale checkout cleanup loop error: %s", exc, exc_info=True)
        await asyncio.sleep(interval)
