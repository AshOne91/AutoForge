import asyncio
import signal
from collections.abc import Iterator
from contextlib import contextmanager
from types import FrameType
from typing import Any


@contextmanager
def shutdown_signal_handlers(stop_event: asyncio.Event) -> Iterator[None]:
    """Translate SIGINT/SIGTERM into an async stop event and restore handlers."""

    loop = asyncio.get_running_loop()
    watched = (signal.SIGINT, signal.SIGTERM)
    previous: dict[signal.Signals, Any] = {}

    def request_shutdown(
        signum: int,
        frame: FrameType | None,
    ) -> None:
        del signum, frame
        loop.call_soon_threadsafe(stop_event.set)

    try:
        for watched_signal in watched:
            previous[watched_signal] = signal.getsignal(watched_signal)
            signal.signal(watched_signal, request_shutdown)
        yield
    finally:
        for watched_signal, handler in previous.items():
            signal.signal(watched_signal, handler)
