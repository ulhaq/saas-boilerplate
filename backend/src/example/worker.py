"""Example background loop, registered in `worker.py`.

Records a `worker_run` row per iteration so the pattern for long-running jobs
(run record committed first, final status written after the work) is in place
for a real product loop to replace.
"""

import asyncio
import logging
from typing import Any

from src.example.config import settings
from src.example.repositories.project import ProjectRepository
from src.platform.core.telemetry import track_worker_run
from src.platform.repositories.worker_run import WorkerRunRepository

log = logging.getLogger(__name__)

WORKER_TYPE = "example_heartbeat"


async def _run_once(session_factory: Any) -> None:
    # Transaction 1: commit the run record so 'running' is immediately visible
    async with session_factory() as session:
        async with session.begin():
            run_id = (await WorkerRunRepository(session).create(WORKER_TYPE)).id

    # Transaction 2: do the work and write the final run status
    async with session_factory() as session:
        async with session.begin():
            project_count = await ProjectRepository(session).unscoped.count()
            await WorkerRunRepository(session).finish(
                run_id=run_id,
                status="success",
                items_processed=project_count,
                changes_detected=0,
                error_count=0,
            )
    log.info("Example heartbeat: %d active project(s)", project_count)


async def run_example_loop(session_factory: Any) -> None:
    interval = settings.heartbeat_interval_seconds
    while True:
        try:
            with track_worker_run(WORKER_TYPE, interval):
                await _run_once(session_factory)
        except Exception as exc:
            log.error("Example loop error: %s", exc, exc_info=True)
        await asyncio.sleep(interval)
