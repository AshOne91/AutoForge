import asyncio
from collections import defaultdict

import pytest

from autoforge.core.event import Event, EventBus, EventHandler
from autoforge.core.pipeline import (
    PipelineCompletedEvent,
    PipelineExecutionError,
    PipelineFailedEvent,
    PipelineStartedEvent,
    PipelineStep,
    SequentialPipeline,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskPolicy,
    TaskRetryScheduledEvent,
    TaskStartedEvent,
)
from autoforge.core.task.task import Task


class RecordingHandler(EventHandler[Event]):
    def __init__(self) -> None:
        self.events: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.events.append(event)


class RecordingTask(Task):
    def __init__(self, name: str, order: list[str]) -> None:
        self._name = name
        self._order = order

    async def execute(self) -> str:
        self._order.append(self._name)
        return f"{self._name}-result"


class FlakyTask(Task):
    def __init__(self, failures: int) -> None:
        self._failures = failures
        self.attempts = 0

    async def execute(self) -> str:
        self.attempts += 1
        if self.attempts <= self._failures:
            raise RuntimeError("temporary failure")
        return "recovered"


class SlowTask(Task):
    async def execute(self) -> None:
        await asyncio.sleep(1)


def _record_all_pipeline_events(bus: EventBus) -> RecordingHandler:
    handler = RecordingHandler()
    event_types = (
        PipelineStartedEvent,
        PipelineCompletedEvent,
        PipelineFailedEvent,
        TaskStartedEvent,
        TaskCompletedEvent,
        TaskFailedEvent,
        TaskRetryScheduledEvent,
    )
    for event_type in event_types:
        bus.subscribe(event_type, handler)
    return handler


def test_pipeline_runs_steps_in_explicit_order_and_publishes_events() -> None:
    order: list[str] = []
    bus = EventBus()
    handler = _record_all_pipeline_events(bus)
    pipeline = SequentialPipeline(
        name="generation",
        job_id="job-1",
        steps=(
            PipelineStep("validate", RecordingTask("validate", order)),
            PipelineStep("generate", RecordingTask("generate", order)),
        ),
        event_bus=bus,
    )

    result = asyncio.run(pipeline.run())

    assert order == ["validate", "generate"]
    assert [execution.result for execution in result.executions] == [
        "validate-result",
        "generate-result",
    ]
    assert [type(event) for event in handler.events] == [
        PipelineStartedEvent,
        TaskStartedEvent,
        TaskCompletedEvent,
        TaskStartedEvent,
        TaskCompletedEvent,
        PipelineCompletedEvent,
    ]
    assert {event.job_id for event in handler.events} == {"job-1"}
    assert {event.correlation_id for event in handler.events} == {"job-1"}


def test_pipeline_retries_only_up_to_the_explicit_policy() -> None:
    bus = EventBus()
    handler = _record_all_pipeline_events(bus)
    task = FlakyTask(failures=1)
    pipeline = SequentialPipeline(
        name="generation",
        job_id="job-2",
        steps=(
            PipelineStep(
                "generate",
                task,
                TaskPolicy(max_attempts=2, retry_delay_seconds=0),
            ),
        ),
        event_bus=bus,
    )

    result = asyncio.run(pipeline.run())

    counts: dict[type[Event], int] = defaultdict(int)
    for event in handler.events:
        counts[type(event)] += 1
    assert task.attempts == 2
    assert result.executions[0].attempts == 2
    assert counts[TaskFailedEvent] == 1
    assert counts[TaskRetryScheduledEvent] == 1
    assert counts[TaskCompletedEvent] == 1
    assert counts[PipelineCompletedEvent] == 1


def test_pipeline_stops_after_timeout_and_reports_failure() -> None:
    order: list[str] = []
    bus = EventBus()
    handler = _record_all_pipeline_events(bus)
    pipeline = SequentialPipeline(
        name="generation",
        job_id="job-3",
        steps=(
            PipelineStep("slow", SlowTask(), TaskPolicy(timeout_seconds=0.01)),
            PipelineStep("never", RecordingTask("never", order)),
        ),
        event_bus=bus,
    )

    with pytest.raises(PipelineExecutionError) as raised:
        asyncio.run(pipeline.run())

    assert raised.value.task_name == "slow"
    assert isinstance(raised.value.__cause__, TimeoutError)
    assert order == []
    assert [type(event) for event in handler.events] == [
        PipelineStartedEvent,
        TaskStartedEvent,
        TaskFailedEvent,
        PipelineFailedEvent,
    ]


def test_pipeline_rejects_duplicate_step_names() -> None:
    task = RecordingTask("same", [])
    with pytest.raises(ValueError, match="unique"):
        SequentialPipeline(
            name="generation",
            job_id="job-4",
            steps=(
                PipelineStep("same", task),
                PipelineStep("same", task),
            ),
            event_bus=EventBus(),
        )
