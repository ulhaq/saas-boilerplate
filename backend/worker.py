"""Standalone background worker - run as a single instance alongside the web process.

Runs the product loop(s), GDPR retention, billing cleanup, and trial reminder
loops. Keeping these out of the web process means horizontal scaling of the API
does not cause duplicate job runs or duplicate emails.

Usage:
    uv run python worker.py
    # or via docker-compose worker service
"""

import asyncio
import logging
import signal

from src.bootstrap import bootstrap
from src.platform.core.database import ASYNC_SESSION_LOCAL
from src.platform.core.logging import setup_logging
from src.platform.core.telemetry import setup_telemetry
from src.platform.services.billing import (
    run_stale_checkout_cleanup_loop,
    run_trial_reminder_loop,
)
from src.platform.services.gdpr import run_gdpr_retention_loop
from src.products import PRODUCTS

setup_logging("worker")
setup_telemetry("worker")
log = logging.getLogger(__name__)


async def main() -> None:
    log.info("Worker starting")
    bootstrap()

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    worker_loops = [
        *(run for product in PRODUCTS for run in product.worker_loops),
        run_gdpr_retention_loop,
        run_stale_checkout_cleanup_loop,
        run_trial_reminder_loop,
    ]
    tasks = [asyncio.create_task(run(ASYNC_SESSION_LOCAL)) for run in worker_loops]

    await stop.wait()
    log.info("Worker shutting down")
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    log.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
