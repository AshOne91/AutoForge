import asyncio

from autoforge.core.audit import AuditRecord


class InMemoryAuditSink:
    """Append-only process-local audit sink for tests and local execution."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []
        self._lock = asyncio.Lock()

    async def append(self, record: AuditRecord) -> None:
        async with self._lock:
            self._records.append(record)

    async def records(self) -> tuple[AuditRecord, ...]:
        async with self._lock:
            return tuple(self._records)
