import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends

from src.platform.core.config import settings
from src.platform.core.database import try_job_lock
from src.platform.core.telemetry import track_worker_run
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.services.base import BaseService
from src.platform.services.billing.common import notify_subscription_managers

log = logging.getLogger(__name__)


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
                self.repos,
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
    interval = settings.billing_trial_reminder_interval_seconds
    while True:
        try:
            with track_worker_run("trial_reminder", interval):
                async with session_factory() as session:
                    async with session.begin():
                        if await try_job_lock(session, "trial_reminder"):
                            service = BillingMaintenanceService(
                                RepositoryManager(session)
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
    interval = settings.billing_cleanup_interval_seconds
    while True:
        try:
            with track_worker_run("stale_checkout_cleanup", interval):
                async with session_factory() as session:
                    async with session.begin():
                        if await try_job_lock(session, "stale_checkout_cleanup"):
                            service = BillingMaintenanceService(
                                RepositoryManager(session)
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
