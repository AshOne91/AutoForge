from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, kw_only=True, slots=True)
class AuditRecord:
    event_id: str
    event_type: str
    event_version: str
    event_created_at: datetime
    correlation_id: str | None
    causation_id: str | None
    job_id: str | None
    producer: str | None
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AuditSink(Protocol):
    async def append(self, record: AuditRecord) -> None: ...
