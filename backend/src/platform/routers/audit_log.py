from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.platform.core.dependencies import require_permission
from src.platform.core.security import Auth
from src.platform.enums import AuditAction, Permission
from src.platform.routers.query_options import PageNumberQuery, PageSizeQuery
from src.platform.schemas.audit_log import AuditLogOut
from src.platform.schemas.common import PaginatedResponse
from src.platform.services.audit_log import AuditLogService

router = APIRouter(prefix="/audit-logs")


@router.get("", status_code=status.HTTP_200_OK)
async def list_audit_logs(
    service: Annotated[AuditLogService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.READ_AUDIT_LOG))],
    page_size: PageSizeQuery = 25,
    page_number: PageNumberQuery = 1,
    action: Annotated[
        AuditAction | None, Query(description="Filter by action type")
    ] = None,
) -> PaginatedResponse[AuditLogOut]:
    return await service.paginate(
        page_size=page_size,
        page_number=page_number,
        action_filter=action,
    )
