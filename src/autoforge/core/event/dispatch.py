from dataclasses import dataclass
from enum import StrEnum

from autoforge.core.event.event import Event
from autoforge.core.event.handler import EventHandler


class HandlerFailurePolicy(StrEnum):
    CRITICAL = "critical"
    OBSERVATIONAL = "observational"


@dataclass(frozen=True, slots=True)
class EventSubscription:
    handler: EventHandler[Event]
    failure_policy: HandlerFailurePolicy


@dataclass(frozen=True, slots=True)
class HandlerDispatchFailure:
    handler_type: str
    failure_policy: HandlerFailurePolicy
    error: Exception


@dataclass(frozen=True, slots=True)
class EventDispatchResult:
    event_id: str
    handler_count: int
    failures: tuple[HandlerDispatchFailure, ...]

    @property
    def succeeded(self) -> bool:
        return not self.failures

    @property
    def critical_failures(self) -> tuple[HandlerDispatchFailure, ...]:
        return tuple(
            failure
            for failure in self.failures
            if failure.failure_policy is HandlerFailurePolicy.CRITICAL
        )


class EventDispatchError(RuntimeError):
    def __init__(self, event: Event, result: EventDispatchResult) -> None:
        critical_count = len(result.critical_failures)
        super().__init__(
            f"Event {event.event_type} ({event.event_id}) failed in "
            f"{critical_count} critical handler(s)"
        )
        self.event = event
        self.result = result
