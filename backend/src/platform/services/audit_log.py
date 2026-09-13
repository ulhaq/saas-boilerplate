from typing import Annotated

from fastapi import Depends

from src.platform.core.dependencies import authenticate
from src.platform.core.security import Auth
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.audit_log import AuditLogOut
from src.platform.schemas.common import PaginatedResponse


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
