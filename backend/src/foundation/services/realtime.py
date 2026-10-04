import asyncio
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends

from src.foundation.core import realtime
from src.foundation.core.config import settings
from src.foundation.core.security import Auth
from src.foundation.core.sse import sse_comment, sse_event
from src.foundation.services.access import authenticate_user_session

# The first event on every stream: the client is subscribed, so it can
# (re-)fetch what it shows without missing a change made in between.
READY_EVENT = "ready"


class EventStreamService:
    """The signed-in user's realtime events (`core/realtime.py`) in their
    current organization, as Server-Sent Events."""

    def __init__(
        self,
        current_user: Annotated[Auth, Depends(authenticate_user_session)],
    ) -> None:
        self.current_user = current_user

    async def stream(self) -> AsyncGenerator[str]:
        """Runs until the client disconnects or `REALTIME_STREAM_MAX_SECONDS`
        pass; the client then reconnects with a current access token."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + settings.realtime_stream_max_seconds
        channel = realtime.user_channel(self.current_user.id)
        async with realtime.broker().subscribe(channel) as subscription:
            yield sse_event("{}", event=READY_EVENT)
            while (remaining := deadline - loop.time()) > 0:
                event = await subscription.next(
                    wait=min(settings.realtime_heartbeat_seconds, remaining),
                )
                if event is None:
                    yield sse_comment("keep-alive")
                elif event.organization_id in (
                    None,
                    self.current_user.organization_id,
                ):
                    yield sse_event(event.to_json(), event=event.type)
