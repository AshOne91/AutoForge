import asyncio

from autoforge.core.metrics import MetricPoint


class InMemoryMetricsSink:
    """Process-local metrics sink for tests and local execution."""

    def __init__(self) -> None:
        self._points: list[MetricPoint] = []
        self._lock = asyncio.Lock()

    async def record(self, point: MetricPoint) -> None:
        async with self._lock:
            self._points.append(point)

    async def points(self) -> tuple[MetricPoint, ...]:
        async with self._lock:
            return tuple(self._points)
