from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, kw_only=True, slots=True)
class MetricPoint:
    """A low-cardinality metric sample derived from an event envelope."""

    name: str
    value: int = 1
    labels: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("metric name must not be empty")
        if self.value < 1:
            raise ValueError("metric value must be positive")


class MetricsSink(Protocol):
    async def record(self, point: MetricPoint) -> None: ...
