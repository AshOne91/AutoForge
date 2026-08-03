import asyncio
from datetime import timedelta
from typing import cast

from autoforge.application.generation import (
    GenerationWorkerLoop,
    GenerationWorkerLoopSettings,
    GenerationWorkerResult,
)
from autoforge.infrastructure.job import InMemoryJobStore


class IdleWorker:
    def __init__(self) -> None:
        self.calls = 0

    async def run_once(self) -> None:
        self.calls += 1


class CompletingWorker:
    def __init__(self) -> None:
        self.cancelled = False

    async def run_once(self) -> GenerationWorkerResult:
        try:
            await asyncio.sleep(0.03)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return cast(GenerationWorkerResult, object())


class BlockingWorker:
    def __init__(self) -> None:
        self.cancelled = False

    async def run_once(self) -> GenerationWorkerResult:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        raise AssertionError("unreachable")


def _settings(*, grace_ms: int = 100) -> GenerationWorkerLoopSettings:
    return GenerationWorkerLoopSettings(
        idle_poll_interval=timedelta(milliseconds=10),
        error_backoff=timedelta(milliseconds=10),
        abandoned_sweep_interval=timedelta(milliseconds=10),
        shutdown_grace_period=timedelta(milliseconds=grace_ms),
    )


def test_worker_loop_idles_without_busy_polling_and_stops() -> None:
    async def scenario() -> None:
        stop = asyncio.Event()
        worker = IdleWorker()
        loop = GenerationWorkerLoop(
            worker=worker,
            job_store=InMemoryJobStore(),
            settings=_settings(),
        )
        asyncio.get_running_loop().call_later(0.035, stop.set)

        result = await loop.run(stop)

        assert 1 <= worker.calls <= 5
        assert result.completed_jobs == 0
        assert result.shutdown_timed_out is False

    asyncio.run(scenario())


def test_worker_loop_allows_current_job_to_finish_during_shutdown() -> None:
    async def scenario() -> None:
        stop = asyncio.Event()
        worker = CompletingWorker()
        loop = GenerationWorkerLoop(
            worker=worker,
            job_store=InMemoryJobStore(),
            settings=_settings(),
        )
        asyncio.get_running_loop().call_later(0.005, stop.set)

        result = await loop.run(stop)

        assert result.completed_jobs == 1
        assert result.shutdown_timed_out is False
        assert worker.cancelled is False

    asyncio.run(scenario())


def test_worker_loop_cancels_current_job_after_shutdown_grace() -> None:
    async def scenario() -> None:
        stop = asyncio.Event()
        worker = BlockingWorker()
        loop = GenerationWorkerLoop(
            worker=worker,
            job_store=InMemoryJobStore(),
            settings=_settings(grace_ms=10),
        )
        asyncio.get_running_loop().call_later(0.005, stop.set)

        result = await loop.run(stop)

        assert result.shutdown_timed_out is True
        assert worker.cancelled is True

    asyncio.run(scenario())
