from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.platform.core.dependencies import authenticate
from src.platform.core.security import Auth
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.common import PaginatedResponse
from src.platform.schemas.notification import NotificationOut, UnreadCountOut


class NotificationService:
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        self.repos = repos
        self.current_user = current_user

    async def list(
        self,
        page_size: int,
        page_number: int,
    ) -> PaginatedResponse[NotificationOut]:
        items, total = await self.repos.notification.list_for_user(
            user_id=self.current_user.id,
            organization_id=self.current_user.organization_id,
            page_size=page_size,
            page_number=page_number,
        )
        return PaginatedResponse(
            items=[NotificationOut.model_validate(n) for n in items],
            page_size=page_size,
            page_number=page_number,
            total=total,
        )

    async def unread_count(self) -> UnreadCountOut:
        count = await self.repos.notification.count_unread(
            user_id=self.current_user.id,
            organization_id=self.current_user.organization_id,
        )
        return UnreadCountOut(count=count)

    async def mark_read(self, notification_id: int) -> NotificationOut:
        notification = await self.repos.notification.get(notification_id)
        if (
            notification is None
            or notification.user_id != self.current_user.id
            or notification.organization_id != self.current_user.organization_id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        notification = await self.repos.notification.mark_read(notification)
        return NotificationOut.model_validate(notification)

    async def mark_all_read(self) -> None:
        await self.repos.notification.mark_all_read(
            user_id=self.current_user.id,
            organization_id=self.current_user.organization_id,
        )
