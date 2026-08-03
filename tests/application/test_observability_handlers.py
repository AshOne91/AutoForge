import asyncio
import logging
from dataclasses import dataclass

from pytest import LogCaptureFixture

from autoforge.application.observability import (
    AuditEventHandler,
    StructuredLoggingEventHandler,
)
from autoforge.core.event import Event
from autoforge.infrastructure.audit import InMemoryAuditSink


@dataclass(frozen=True, kw_only=True, slots=True)
class SensitiveEvent(Event):
    secret: str


def test_structured_logging_records_envelope_without_payload(
    caplog: LogCaptureFixture,
) -> None:
    logger = logging.getLogger("autoforge.test.observability")
    handler = StructuredLoggingEventHandler(logger)
    event = SensitiveEvent(
        secret="must-not-be-logged",
        job_id="job-1",
        producer="test",
    )

    with caplog.at_level(logging.INFO, logger=logger.name):
        asyncio.run(handler.handle(event))

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.getMessage() == "autoforge event SensitiveEvent"
    assert record.autoforge_event_id == event.event_id  # type: ignore[attr-defined]
    assert record.autoforge_job_id == "job-1"  # type: ignore[attr-defined]
    assert "must-not-be-logged" not in caplog.text
    assert not hasattr(record, "secret")


def test_audit_handler_appends_envelope_without_payload() -> None:
    async def scenario() -> None:
        sink = InMemoryAuditSink()
        handler = AuditEventHandler(sink)
        event = SensitiveEvent(
            secret="must-not-be-audited",
            job_id="job-2",
            correlation_id="correlation-1",
        )

        await handler.handle(event)

        records = await sink.records()
        assert len(records) == 1
        record = records[0]
        assert record.event_id == event.event_id
        assert record.event_type == "SensitiveEvent"
        assert record.correlation_id == "correlation-1"
        assert record.job_id == "job-2"
        assert not hasattr(record, "secret")

    asyncio.run(scenario())
