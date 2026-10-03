"""Worker job locks: a job's iteration runs in one worker at a time."""

import asyncio

import pytest

from src.billing.services.maintenance import (
    run_stale_checkout_cleanup_loop,
    run_trial_reminder_loop,
)
from src.platform.core.database import try_job_lock
from src.platform.services.gdpr import run_gdpr_retention_loop
from tests.conftest import TestSessionLocal


async def test_a_job_lock_is_held_until_the_transaction_ends():
    async with TestSessionLocal() as first, first.begin():
        assert await try_job_lock(first, "job-a") is True
        async with TestSessionLocal() as second, second.begin():
            assert await try_job_lock(second, "job-a") is False
            assert await try_job_lock(second, "job-b") is True

    async with TestSessionLocal() as third, third.begin():
        assert await try_job_lock(third, "job-a") is True


async def _run_one_iteration(loop, mocker) -> None:
    """Run a worker loop for exactly one iteration."""
    mocker.patch("asyncio.sleep", side_effect=asyncio.CancelledError)
    with pytest.raises(asyncio.CancelledError):
        await loop(TestSessionLocal)


LOOPS = [
    pytest.param(
        "trial_reminder",
        run_trial_reminder_loop,
        "src.billing.services.maintenance."
        "BillingMaintenanceService.send_trial_reminders",
        id="trial-reminders",
    ),
    pytest.param(
        "stale_checkout_cleanup",
        run_stale_checkout_cleanup_loop,
        "src.billing.services.maintenance."
        "BillingMaintenanceService.cleanup_stale_checkouts",
        id="stale-checkout-cleanup",
    ),
    pytest.param(
        "gdpr_retention",
        run_gdpr_retention_loop,
        "src.platform.services.gdpr.purge_expired_tokens",
        id="gdpr-retention",
    ),
]


@pytest.mark.parametrize(("job", "loop", "work"), LOOPS)
async def test_an_iteration_runs_when_no_other_worker_holds_the_job(
    job, loop, work, mocker
):
    do_work = mocker.patch(work, return_value=0)
    await _run_one_iteration(loop, mocker)
    do_work.assert_called_once()


@pytest.mark.parametrize(("job", "loop", "work"), LOOPS)
async def test_an_iteration_is_skipped_while_another_worker_runs_the_job(
    job, loop, work, mocker
):
    do_work = mocker.patch(work, return_value=0)
    async with TestSessionLocal() as other_worker, other_worker.begin():
        assert await try_job_lock(other_worker, job)
        await _run_one_iteration(loop, mocker)
    do_work.assert_not_called()
