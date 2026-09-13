from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.platform.core.config import settings
from src.platform.models.audit_log import AuditLog
from src.platform.repositories.abc import RepositoryABC


class AuditLogRepository(RepositoryABC[AuditLog]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(AuditLog, db)

    async def create(
        self,
        *,
        action: str,
        organization_id: int | None = None,
        user_id: int | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        instance = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details,
        )
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def paginate(
        self,
        organization_id: int,
        page_size: int,
        page_number: int,
        action_filter: str | None = None,
    ) -> tuple[Sequence[AuditLog], int]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .options(selectinload(AuditLog.user))
        )
        if action_filter:
            stmt = stmt.where(AuditLog.action == action_filter)
        stmt = (
            stmt.order_by(AuditLog.created_at.desc())
            .offset((page_number - 1) * page_size)
            .limit(page_size)
        )
        rs = await self.db.execute(stmt)
        items = rs.scalars().all()

        count_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.organization_id == organization_id)
        )
        if action_filter:
            count_stmt = count_stmt.where(AuditLog.action == action_filter)
        count_rs = await self.db.execute(count_stmt)
        total = int(count_rs.scalar_one())

        return items, total

    async def get_all_for_user(self, user_id: int) -> Sequence[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(settings.gdpr_export_audit_log_limit)
        )
        rs = await self.db.execute(stmt)
        return rs.scalars().all()
