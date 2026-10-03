from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.platform.core.security import Auth
from src.platform.enums import Permission
from src.platform.routers.query_options import PageNumberQuery, PageSizeQuery
from src.platform.schemas.audit_log import AuditLogOut
from src.platform.schemas.common import PaginatedResponse
from src.platform.services.access import require_permission
from src.platform.services.audit_log import AuditLogService


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
