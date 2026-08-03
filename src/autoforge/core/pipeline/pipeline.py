import asyncio
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from autoforge.core.event import Event, EventBus
from autoforge.core.task.task import Task


@dataclass(frozen=True, kw_only=True, slots=True)
class PipelineStartedEvent(Event):
    pipeline_name: str


@dataclass(frozen=True, kw_only=True, slots=True)
class PipelineCompletedEvent(Event):
    pipeline_name: str
    duration_seconds: float


@dataclass(frozen=True, kw_only=True, slots=True)
class PipelineFailedEvent(Event):
    pipeline_name: str
    task_name: str
    error_type: str


@dataclass(frozen=True, kw_only=True, slots=True)
class PipelineCancelledEvent(Event):
    pipeline_name: str
    task_name: str | None


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskStartedEvent(Event):
    pipeline_name: str
    task_name: str
    attempt: int


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskCompletedEvent(Event):
    pipeline_name: str
    task_name: str
    attempt: int
    duration_seconds: float


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskFailedEvent(Event):
    pipeline_name: str
    task_name: str
    attempt: int
    error_type: str


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskRetryScheduledEvent(Event):
    pipeline_name: str
    task_name: str
    failed_attempt: int
    next_attempt: int
    delay_seconds: float
    error_type: str


@dataclass(frozen=True, slots=True)
class TaskPolicy:
    max_attempts: int = 1
    timeout_seconds: float | None = None
    retry_delay_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        if self.retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must not be negative")


@dataclass(frozen=True, slots=True)
class PipelineStep:
    name: str
    task: Task
    policy: TaskPolicy = field(default_factory=TaskPolicy)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("PipelineStep name must not be empty")


@dataclass(frozen=True, slots=True)
class TaskExecution:
    task_name: str
    attempts: int
    result: Any


@dataclass(frozen=True, slots=True)
class PipelineResult:
    pipeline_name: str
    executions: tuple[TaskExecution, ...]


class PipelineExecutionError(RuntimeError):
    def __init__(self, pipeline_name: str, task_name: str, cause: Exception) -> None:
        super().__init__(f"Pipeline {pipeline_name!r} failed at task {task_name!r}")
        self.pipeline_name = pipeline_name
        self.task_name = task_name
        self.__cause__ = cause


class Pipeline(ABC):
    """Asynchronous pipeline contract."""

    @abstractmethod
    async def run(self) -> PipelineResult: ...


class SequentialPipeline(Pipeline):
    """Run explicit task steps sequentially with retry and timeout policies."""

    def __init__(
        self,
        *,
        name: str,
        job_id: str,
        steps: Sequence[PipelineStep],
        event_bus: EventBus,
    ) -> None:
        if not name.strip():
            raise ValueError("Pipeline name must not be empty")
        if not job_id.strip():
            raise ValueError("job_id must not be empty")
        if not steps:
            raise ValueError("Pipeline must contain at least one step")
        names = [step.name for step in steps]
        if len(names) != len(set(names)):
            raise ValueError("Pipeline step names must be unique")
        self._name = name
        self._job_id = job_id
        self._steps = tuple(steps)
        self._event_bus = event_bus

    async def run(self) -> PipelineResult:
        pipeline_started = PipelineStartedEvent(
            pipeline_name=self._name,
            job_id=self._job_id,
            correlation_id=self._job_id,
            producer="pipeline",
        )
        await self._event_bus.publish(pipeline_started)
        started_at = monotonic()
        executions: list[TaskExecution] = []
        current_task: str | None = None

        try:
            for step in self._steps:
                current_task = step.name
                executions.append(await self._execute_step(step, pipeline_started))
        except asyncio.CancelledError:
            await self._event_bus.publish(
                PipelineCancelledEvent(
                    pipeline_name=self._name,
                    task_name=current_task,
                    **self._metadata(pipeline_started.event_id),
                )
            )
            raise
        except Exception as error:
            assert current_task is not None
            await self._event_bus.publish(
                PipelineFailedEvent(
                    pipeline_name=self._name,
                    task_name=current_task,
                    error_type=type(error).__name__,
                    **self._metadata(pipeline_started.event_id),
                )
            )
            raise PipelineExecutionError(self._name, current_task, error) from error

        await self._event_bus.publish(
            PipelineCompletedEvent(
                pipeline_name=self._name,
                duration_seconds=monotonic() - started_at,
                **self._metadata(pipeline_started.event_id),
            )
        )
        return PipelineResult(self._name, tuple(executions))

    async def _execute_step(
        self, step: PipelineStep, pipeline_started: PipelineStartedEvent
    ) -> TaskExecution:
        for attempt in range(1, step.policy.max_attempts + 1):
            task_started = TaskStartedEvent(
                pipeline_name=self._name,
                task_name=step.name,
                attempt=attempt,
                **self._metadata(pipeline_started.event_id),
            )
            await self._event_bus.publish(task_started)
            started_at = monotonic()
            try:
                result = await self._execute_task(step)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                await self._event_bus.publish(
                    TaskFailedEvent(
                        pipeline_name=self._name,
                        task_name=step.name,
                        attempt=attempt,
                        error_type=type(error).__name__,
                        **self._metadata(task_started.event_id),
                    )
                )
                if attempt == step.policy.max_attempts:
                    raise
                await self._event_bus.publish(
                    TaskRetryScheduledEvent(
                        pipeline_name=self._name,
                        task_name=step.name,
                        failed_attempt=attempt,
                        next_attempt=attempt + 1,
                        delay_seconds=step.policy.retry_delay_seconds,
                        error_type=type(error).__name__,
                        **self._metadata(task_started.event_id),
                    )
                )
                if step.policy.retry_delay_seconds:
                    await asyncio.sleep(step.policy.retry_delay_seconds)
                continue

            await self._event_bus.publish(
                TaskCompletedEvent(
                    pipeline_name=self._name,
                    task_name=step.name,
                    attempt=attempt,
                    duration_seconds=monotonic() - started_at,
                    **self._metadata(task_started.event_id),
                )
            )
            return TaskExecution(step.name, attempt, result)
        raise AssertionError("unreachable")

    async def _execute_task(self, step: PipelineStep) -> Any:
        if step.policy.timeout_seconds is None:
            return await step.task.execute()
        return await asyncio.wait_for(
            step.task.execute(), timeout=step.policy.timeout_seconds
        )

    def _metadata(self, causation_id: str) -> dict[str, str]:
        return {
            "job_id": self._job_id,
            "correlation_id": self._job_id,
            "causation_id": causation_id,
            "producer": "pipeline",
        }
