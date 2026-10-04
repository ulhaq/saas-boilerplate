import asyncio
import signal
from collections.abc import AsyncGenerator, Iterator

import pytest

from src.foundation.core import shutdown
from src.foundation.core.sse import EventSourceResponse


@pytest.fixture(autouse=True)
def unwatched() -> Iterator[None]:
    yield
    shutdown._event = None


@pytest.fixture
def server_sigterm_handler() -> Iterator[list[int]]:
    """Stands in for uvicorn's SIGTERM handler; records the signals it got."""
    received: list[int] = []
    original = signal.signal(signal.SIGTERM, lambda sig, _frame: received.append(sig))
    yield received
    signal.signal(signal.SIGTERM, original)


async def _body(response: EventSourceResponse) -> AsyncGenerator[str]:
    async for chunk in response.body_iterator:
        yield chunk if isinstance(chunk, str) else bytes(chunk).decode()


async def test_signal_reaches_the_server_and_sets_shutting_down(
    server_sigterm_handler: list[int],
) -> None:
    shutdown.watch_shutdown_signals()
    event = shutdown.shutting_down()
    assert event is not None
    assert not event.is_set()

    signal.raise_signal(signal.SIGTERM)
    await asyncio.wait_for(event.wait(), timeout=1)

    assert server_sigterm_handler == [signal.SIGTERM]


async def test_an_open_stream_ends_when_the_server_shuts_down() -> None:
    shutdown.watch_shutdown_signals()
    stop = shutdown.shutting_down()
    assert stop is not None
    cleaned_up = asyncio.Event()

    async def endless() -> AsyncGenerator[str]:
        try:
            yield "first"
            await asyncio.Event().wait()  # an idle stream
            yield "never"
        finally:
            cleaned_up.set()

    body = _body(EventSourceResponse(endless()))
    assert await anext(body) == "first"

    pending = asyncio.ensure_future(anext(body))
    await asyncio.sleep(0)
    stop.set()

    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(pending, timeout=1)
    assert cleaned_up.is_set()


async def test_a_stream_runs_to_its_end_while_the_server_runs() -> None:
    shutdown.watch_shutdown_signals()

    async def finite() -> AsyncGenerator[str]:
        for chunk in ("a", "b", "c"):
            yield chunk

    assert [c async for c in _body(EventSourceResponse(finite()))] == ["a", "b", "c"]


async def test_streams_work_without_a_watcher() -> None:
    async def finite() -> AsyncGenerator[str]:
        yield "a"

    assert [c async for c in _body(EventSourceResponse(finite()))] == ["a"]
