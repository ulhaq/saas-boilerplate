from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.foundation.core.sse import SSE_MEDIA_TYPE, EventSourceResponse
from src.foundation.services.realtime import EventStreamService

router = APIRouter(prefix="/events")


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_class=EventSourceResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "The user's realtime events, as Server-Sent Events",
            "content": {SSE_MEDIA_TYPE: {"schema": {"type": "string"}}},
        },
    },
)
async def stream_events(
    service: Annotated[EventStreamService, Depends()],
) -> EventSourceResponse:
    return EventSourceResponse(service.stream())
