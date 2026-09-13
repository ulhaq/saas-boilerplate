from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.worker_run import WorkerRun


class WorkerRunRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, worker_type: str) -> WorkerRun:
        run = WorkerRun(worker_type=worker_type, started_at=datetime.now(UTC))
        self.db.add(run)
        await self.db.flush()
        return run

    async def finish(
        self,
        run_id: int,
        status: str,
        items_processed: int,
        changes_detected: int,
        error_count: int,
    ) -> None:
        await self.db.execute(
            update(WorkerRun)
            .where(WorkerRun.id == run_id)
            .values(
                finished_at=datetime.now(UTC),
                status=status,
                items_processed=items_processed,
                changes_detected=changes_detected,
                error_count=error_count,
            )
        )

    async def get_latest(self, worker_type: str | None = None) -> WorkerRun | None:
        stmt = select(WorkerRun)
        if worker_type is not None:
            stmt = stmt.where(WorkerRun.worker_type == worker_type)
        stmt = stmt.order_by(WorkerRun.started_at.desc()).limit(1)
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()
