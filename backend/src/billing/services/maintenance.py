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


# A push failing this often is given up (logged as an error, left pending):
# with the backoff below that is about four hours of retries.
MAX_CUSTOMER_SYNC_ATTEMPTS = 8


async def sync_customer_emails(
    session_factory: Any, provider: BillingProviderABC
) -> int:
    """Push pending customer emails (`BillingAccount.pending_customer_email`)
    to the provider. A failed push is retried with exponential backoff, up to
    `MAX_CUSTOMER_SYNC_ATTEMPTS` - a failing account never blocks the others;
    a push is only marked done if no newer email replaced it meanwhile.
    Returns how many were synced.

    No transaction is open during a provider call: the pending accounts are
    read in one short transaction and each is cleared in its own, so a slow
    or failing provider never holds a connection or blocks a writer. That
    also makes it safe to run in several workers at once (no job lock): two
    pushing the same email is harmless, and the clear compares first.
    """
    async with session_factory() as session, session.begin():
        accounts = await BillingRepositoryManager(
            session
        ).billing_account.get_due_customer_syncs(MAX_CUSTOMER_SYNC_ATTEMPTS)
        pending = [
            (
                account.id,
                account.external_customer_id,
                account.pending_customer_email,
                account.customer_sync_attempts,
            )
            for account in accounts
        ]

    synced = 0
    for account_id, customer_id, email, attempts in pending:
        if customer_id is None or email is None:
            continue
        try:
            await provider.update_customer(customer_id, email=email)
        except Exception as exc:
            await _record_failure(
                session_factory, account_id, customer_id, email, attempts, exc
            )
            continue
        async with session_factory() as session, session.begin():
            repo = BillingRepositoryManager(session).billing_account
            if await repo.clear_pending_customer_email(account_id, email):
                synced += 1
    return synced


async def _record_failure(
    session_factory: Any,
    account_id: int,
    customer_id: str,
    email: str,
    previous_attempts: int,
    exc: Exception,
) -> None:
    # The first retry after 2 minutes, doubling each time.
    retry_at = datetime.now(UTC) + timedelta(minutes=2 ** (previous_attempts + 1))
    async with session_factory() as session, session.begin():
        attempts = await BillingRepositoryManager(
            session
        ).billing_account.record_customer_sync_failure(account_id, email, retry_at)
    if attempts is None:
        return  # a newer email replaced it; that one starts fresh
    if attempts >= MAX_CUSTOMER_SYNC_ATTEMPTS:
        log.error(
            "Customer sync gave up after %d attempts [customer=%s]: %s",
            attempts,
            customer_id,
            exc,
        )
    else:
        log.warning(
            "Customer sync failed, retrying [customer=%s attempt=%d]: %s",
            customer_id,
            attempts,
            exc,
        )


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
                count = await sync_customer_emails(
                    session_factory, get_billing_provider()
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
