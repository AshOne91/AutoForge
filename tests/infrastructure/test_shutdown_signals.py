import asyncio
import signal
from collections.abc import Callable
from types import FrameType

from autoforge.infrastructure.process import shutdown_signal_handlers


def test_shutdown_signals_set_event_and_restore_handlers(monkeypatch) -> None:
    async def scenario() -> None:
        stop = asyncio.Event()
        installed: dict[
            signal.Signals, Callable[[int, FrameType | None], None] | object
        ] = {}
        original = object()

        monkeypatch.setattr(signal, "getsignal", lambda _: original)

        def record_handler(watched_signal, handler) -> None:
            installed[watched_signal] = handler

        monkeypatch.setattr(signal, "signal", record_handler)

        with shutdown_signal_handlers(stop):
            handler = installed[signal.SIGTERM]
            assert callable(handler)
            handler(signal.SIGTERM, None)
            await asyncio.sleep(0)
            assert stop.is_set()

        assert installed[signal.SIGINT] is original
        assert installed[signal.SIGTERM] is original

    asyncio.run(scenario())
