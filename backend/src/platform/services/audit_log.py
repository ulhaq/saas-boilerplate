from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.core.security import Auth
from src.platform.enums import AuditAction
from src.platform.repositories.audit_log import AuditLogRepository
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.audit_log import AuditLogOut
from src.platform.schemas.common import PaginatedResponse
from src.platform.services.access import authenticate


class AuditLogService:
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        self.repos = repos
        self.current_user = current_user

    async def paginate(
        self,
        page_size: int,
        page_number: int,
        action_filter: str | None = None,
    ) -> PaginatedResponse[AuditLogOut]:
        items, total = await self.repos.audit_log.paginate(
            organization_id=self.current_user.organization_id,
            page_size=page_size,
            page_number=page_number,
            action_filter=action_filter,
        )
        return PaginatedResponse(
            items=[AuditLogOut.model_validate(item) for item in items],
            page_size=page_size,
            page_number=page_number,
            total=total,
        )


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
