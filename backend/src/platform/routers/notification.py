from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.platform.routers.query_options import PageNumberQuery, PageSizeQuery
from src.platform.schemas.common import PaginatedResponse
from src.platform.schemas.notification import NotificationOut, UnreadCountOut
from src.platform.services.notification import NotificationService

router = APIRouter(prefix="/notifications")


@router.get("", status_code=status.HTTP_200_OK)
async def list_notifications(
    service: Annotated[NotificationService, Depends()],
    page_size: PageSizeQuery = 25,
    page_number: PageNumberQuery = 1,
) -> PaginatedResponse[NotificationOut]:
    return await service.list(page_size=page_size, page_number=page_number)


@router.get("/unread-count", status_code=status.HTTP_200_OK)
async def unread_count(
    service: Annotated[NotificationService, Depends()],
) -> UnreadCountOut:
    return await service.unread_count()


@router.post("/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_read(
    notification_id: int,
    service: Annotated[NotificationService, Depends()],
) -> NotificationOut:
    return await service.mark_read(notification_id)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    service: Annotated[NotificationService, Depends()],
) -> None:
    await service.mark_all_read()
