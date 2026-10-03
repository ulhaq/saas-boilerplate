"""Billing's worker loops take their job lock: an iteration runs in one worker
at a time (the foundation's `try_job_lock`). The customer sync is the exception -
it is safe to run concurrently (see `sync_customer_emails`)."""

import pytest

from src.billing.services.maintenance import (
    run_stale_checkout_cleanup_loop,
    run_trial_reminder_loop,
)
from src.foundation.core.database import try_job_lock
from tests.conftest import TestSessionLocal
from tests.unit.test_worker_job_lock import run_one_iteration

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
]


@pytest.mark.usefixtures("job")
@pytest.mark.parametrize(("job", "loop", "work"), LOOPS)
async def test_an_iteration_runs_when_no_other_worker_holds_the_job(loop, work, mocker):
    do_work = mocker.patch(work, return_value=0)
    await run_one_iteration(loop, mocker)
    do_work.assert_called_once()


@pytest.mark.parametrize(("job", "loop", "work"), LOOPS)
async def test_an_iteration_is_skipped_while_another_worker_runs_the_job(
    job,
    loop,
    work,
    mocker,
):
    do_work = mocker.patch(work, return_value=0)
    async with TestSessionLocal() as other_worker, other_worker.begin():
        assert await try_job_lock(other_worker, job)
        await run_one_iteration(loop, mocker)
    do_work.assert_not_called()
