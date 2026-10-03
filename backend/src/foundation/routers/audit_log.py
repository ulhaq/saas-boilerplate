from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.foundation.core.security import Auth
from src.foundation.enums import Permission
from src.foundation.routers.query_options import PageNumberQuery, PageSizeQuery
from src.foundation.schemas.audit_log import AuditLogOut
from src.foundation.schemas.common import PaginatedResponse
from src.foundation.services.access import require_permission
from src.foundation.services.audit_log import AuditLogService


def build_router(audit_actions: type[StrEnum]) -> APIRouter:
    """The audit-log routes, filtering by ``audit_actions``: every action the
    installed modules record, composed by the assembly layer
    (`src.bootstrap.AUDIT_ACTION`)."""
    router = APIRouter(prefix="/audit-logs")

    @router.get("", status_code=status.HTTP_200_OK)
    async def list_audit_logs(
        service: Annotated[AuditLogService, Depends()],
        _: Annotated[Auth, Depends(require_permission(Permission.READ_AUDIT_LOG))],
        page_size: PageSizeQuery = 25,
        page_number: PageNumberQuery = 1,
        action: Annotated[
            audit_actions | None,  # ty: ignore[invalid-type-form]
            Query(description="Filter by action type"),
        ] = None,
    ) -> PaginatedResponse[AuditLogOut]:
        return await service.paginate(
            page_size=page_size,
            page_number=page_number,
            action_filter=action,
        )

    return router
