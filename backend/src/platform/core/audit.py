from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.enums import AuditAction
from src.platform.repositories.audit_log import AuditLogRepository


async def write_audit_log(
    session: AsyncSession,
    *,
    action: AuditAction,
    organization_id: int | None = None,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Write an audit log entry from a background task (no request context, no IP)."""
    await AuditLogRepository(session).create(
        action=action,
        organization_id=organization_id,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=None,
        details=details,
    )
