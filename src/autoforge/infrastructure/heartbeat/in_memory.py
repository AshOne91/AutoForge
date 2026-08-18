import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from autoforge.core.heartbeat import ServiceHeartbeat, ServiceHeartbeatReport


class InMemoryServiceHeartbeatStore:
    """Process-local heartbeat store for HTTP tests and local control-plane use."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._records: dict[tuple[str, str], ServiceHeartbeat] = {}
        self._lock = asyncio.Lock()

    async def record(
        self,
        report: ServiceHeartbeatReport,
        *,
        ttl: timedelta,
    ) -> ServiceHeartbeat:
        if ttl <= timedelta(0):
            raise ValueError("ttl must be positive")
        reported_at = self._now()
        heartbeat = ServiceHeartbeat(
            **report.model_dump(),
            reported_at=reported_at,
            expires_at=reported_at + ttl,
        )
        async with self._lock:
            self._records[(report.service_name, report.instance_id)] = heartbeat
        return heartbeat

    async def list_active(self) -> tuple[ServiceHeartbeat, ...]:
        now = self._now()
        async with self._lock:
            return tuple(
                heartbeat
                for _, heartbeat in sorted(self._records.items())
                if heartbeat.expires_at > now
            )

    def _now(self) -> datetime:
        now = self._clock()
        if now.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return now
