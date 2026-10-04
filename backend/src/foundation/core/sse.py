"""Server-Sent Events wire format and response
(https://html.spec.whatwg.org/multipage/server-sent-events.html)."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator, AsyncIterable, Mapping

from fastapi.responses import StreamingResponse

from src.foundation.core.shutdown import shutting_down

SSE_MEDIA_TYPE = "text/event-stream"


def sse_event(data: str, *, event: str | None = None) -> str:
    """One event; multi-line ``data`` is split into several ``data:`` lines."""
    lines = [f"event: {event}"] if event else []
    lines += [f"data: {line}" for line in data.splitlines() or [""]]
    return "\n".join(lines) + "\n\n"


def sse_comment(text: str) -> str:
    """A comment line - ignored by clients, keeps idle connections alive."""
    return f": {text}\n\n"


async def _until_shutdown(content: AsyncIterable[str]) -> AsyncGenerator[str]:
    """``content``, ended early once the server starts shutting down - else
    the server waits for the stream before it can exit (`core/shutdown.py`)."""
    stop = shutting_down()
    if stop is None:
        async for chunk in content:
            yield chunk
        return
    events = aiter(content)
    stopped = asyncio.ensure_future(stop.wait())
    try:
        while True:
            chunk = asyncio.ensure_future(anext(events))
            await asyncio.wait({chunk, stopped}, return_when=asyncio.FIRST_COMPLETED)
            if not chunk.done():
                chunk.cancel()
                with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
                    await chunk
                return
            try:
                yield chunk.result()
            except StopAsyncIteration:
                return
    finally:
        stopped.cancel()
        if isinstance(events, AsyncGenerator):
            await events.aclose()


class EventSourceResponse(StreamingResponse):
    """Streams ``content`` as ``text/event-stream``, unbuffered and
    untransformed by proxies (`no-transform` also keeps Caddy's `encode` from
    gzipping - and so buffering - it; `X-Accel-Buffering` is nginx's switch).
    The stream ends when the server starts shutting down."""

    media_type = SSE_MEDIA_TYPE

    def __init__(
        self,
        content: AsyncIterable[str],
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(
            _until_shutdown(content),
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
                **(headers or {}),
            },
        )
