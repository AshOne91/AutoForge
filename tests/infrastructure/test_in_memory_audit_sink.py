import asyncio
from datetime import UTC, datetime

from autoforge.core.audit import AuditRecord
from autoforge.infrastructure.audit import InMemoryAuditSink


def _record(event_id: str) -> AuditRecord:
    return AuditRecord(
        event_id=event_id,
        event_type="SampleEvent",
        event_version="1",
        event_created_at=datetime.now(UTC),
        correlation_id=event_id,
        causation_id=None,
        job_id=None,
        producer="test",
    )


def test_sink_is_append_only_and_returns_snapshot() -> None:
    async def scenario() -> None:
        sink = InMemoryAuditSink()
        first = _record("event-1")
        second = _record("event-2")

        await sink.append(first)
        snapshot = await sink.records()
        await sink.append(second)

        assert snapshot == (first,)
        assert await sink.records() == (first, second)

    asyncio.run(scenario())
