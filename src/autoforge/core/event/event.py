from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


def _new_id() -> str:
    return str(uuid4())


@dataclass(frozen=True, kw_only=True, slots=True)
class Event:
    """Base class for immutable in-process domain events."""

    event_id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_version: str = "1"
    correlation_id: str | None = None
    causation_id: str | None = None
    job_id: str | None = None
    producer: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must not be empty")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        if not self.event_version:
            raise ValueError("event_version must not be empty")
        if self.correlation_id is None:
            object.__setattr__(self, "correlation_id", self.event_id)

    @property
    def event_type(self) -> str:
        """Return the stable, serializable Python event type name."""

        return type(self).__name__
