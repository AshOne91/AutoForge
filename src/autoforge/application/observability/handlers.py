import logging

from autoforge.core.audit import AuditRecord, AuditSink
from autoforge.core.event import Event, EventHandler
from autoforge.core.metrics import MetricPoint, MetricsSink


class StructuredLoggingEventHandler(EventHandler[Event]):
    """Log only the common event envelope, never arbitrary event payload fields."""

    def __init__(self, logger: logging.Logger, *, level: int = logging.INFO) -> None:
        self._logger = logger
        self._level = level

    async def handle(self, event: Event) -> None:
        self._logger.log(
            self._level,
            "autoforge event %s",
            event.event_type,
            extra={
                "autoforge_event_id": event.event_id,
                "autoforge_event_type": event.event_type,
                "autoforge_event_version": event.event_version,
                "autoforge_correlation_id": event.correlation_id,
                "autoforge_causation_id": event.causation_id,
                "autoforge_job_id": event.job_id,
                "autoforge_producer": event.producer,
            },
        )


class AuditEventHandler(EventHandler[Event]):
    """Append an envelope-only audit record to an injected sink."""

    def __init__(self, sink: AuditSink) -> None:
        self._sink = sink

    async def handle(self, event: Event) -> None:
        await self._sink.append(
            AuditRecord(
                event_id=event.event_id,
                event_type=event.event_type,
                event_version=event.event_version,
                event_created_at=event.created_at,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
                job_id=event.job_id,
                producer=event.producer,
            )
        )


class MetricsEventHandler(EventHandler[Event]):
    """Record one low-cardinality event metric without inspecting its payload."""

    def __init__(self, sink: MetricsSink) -> None:
        self._sink = sink

    async def handle(self, event: Event) -> None:
        await self._sink.record(
            MetricPoint(
                name="autoforge.events.received",
                labels=(
                    ("event_type", event.event_type),
                    ("event_version", event.event_version),
                ),
            )
        )
