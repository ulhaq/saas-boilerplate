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
from src.example.worker import run_example_loop
from src.platform.services.billing import (
    run_stale_checkout_cleanup_loop,
    run_trial_reminder_loop,
)
from src.platform.services.gdpr import run_gdpr_retention_loop

setup_logging("worker")
log = logging.getLogger(__name__)


async def main() -> None:
    log.info("Worker starting")
    bootstrap()

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    tasks = [
        asyncio.create_task(run_example_loop(ASYNC_SESSION_LOCAL)),
        asyncio.create_task(run_gdpr_retention_loop(ASYNC_SESSION_LOCAL)),
        asyncio.create_task(run_stale_checkout_cleanup_loop(ASYNC_SESSION_LOCAL)),
        asyncio.create_task(run_trial_reminder_loop(ASYNC_SESSION_LOCAL)),
    ]

    await stop.wait()
    log.info("Worker shutting down")
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    log.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
