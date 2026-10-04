"""Tells long-lived responses that the server is shutting down.

On SIGINT/SIGTERM (a deploy, Ctrl+C, a dev-server reload) uvicorn stops
accepting connections and then waits - without a timeout - for every open
response to finish before it exits. An event stream (`GET /v1/events`) would
keep it waiting for up to `REALTIME_STREAM_MAX_SECONDS`, while the new process
can't start. `EventSourceResponse` (`core/sse.py`) ends its stream as soon as
`shutting_down()` is set; the app reconnects to the next process.
"""

import asyncio
import signal
import threading
from collections.abc import Callable
from types import FrameType
from typing import Any

_SIGNALS = (signal.SIGINT, signal.SIGTERM)

_event: asyncio.Event | None = None


def shutting_down() -> asyncio.Event | None:
    """Set once the server has been asked to stop; None when not watched."""
    return _event


def watch_shutdown_signals() -> None:
    """Chain onto the server's SIGINT/SIGTERM handlers. Call from the app's
    lifespan startup: uvicorn has installed its handlers by then. Does nothing
    off the main thread (signals can't be handled there - e.g. TestClient) or
    without a server handler to chain onto."""
    global _event  # noqa: PLW0603 - one server per process
    _event = asyncio.Event()
    if threading.current_thread() is not threading.main_thread():
        return
    event, loop = _event, asyncio.get_running_loop()
    for sig in _SIGNALS:
        previous = signal.getsignal(sig)
        # SIG_DFL / SIG_IGN / None: no server handler to chain onto.
        if previous is None or isinstance(previous, int):
            continue
        signal.signal(sig, _chained(previous, loop, event))


def _chained(
    previous: Callable[[int, FrameType | None], Any],
    loop: asyncio.AbstractEventLoop,
    event: asyncio.Event,
) -> Callable[[int, FrameType | None], None]:
    def handler(signum: int, frame: FrameType | None) -> None:
        loop.call_soon_threadsafe(event.set)
        previous(signum, frame)

    return handler
