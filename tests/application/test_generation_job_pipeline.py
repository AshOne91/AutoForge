import asyncio
from pathlib import Path

import pytest

from autoforge.application.generation import (
    GenerationJobPipeline,
    GenerationJobRequest,
)
from autoforge.core.event import Event, EventBus, EventHandler
from autoforge.core.job import (
    GenerationCompletedEvent,
    GenerationJobCreatedEvent,
    GenerationJobStatus,
    GenerationStartedEvent,
    ValidationCompletedEvent,
    ValidationFailedEvent,
    ValidationStartedEvent,
)
from autoforge.core.pipeline import PipelineExecutionError
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.job import InMemoryJobStore
from autoforge.services.validation import (
    ProcessResult,
    ProjectValidationResult,
    ValidationStep,
    ValidationStepResult,
)


class RecordingHandler(EventHandler[Event]):
    def __init__(self) -> None:
        self.events: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.events.append(event)


class SuccessfulValidator:
    async def validate(
        self, *, package_name: str, workspace: Workspace
    ) -> ProjectValidationResult:
        assert package_name == "sample"
        assert workspace.root.is_dir()
        return ProjectValidationResult(
            steps=(
                _validation_step(ValidationStep.IMPORT, succeeded=True),
                _validation_step(ValidationStep.PYTEST, succeeded=True),
                _validation_step(ValidationStep.RUFF, succeeded=True),
                _validation_step(ValidationStep.PACKAGE_BUILD, succeeded=True),
            )
        )


class FailingValidator:
    async def validate(
        self, *, package_name: str, workspace: Workspace
    ) -> ProjectValidationResult:
        del package_name, workspace
        return ProjectValidationResult(
            steps=(_validation_step(ValidationStep.RUFF, succeeded=False),)
        )


def _validation_step(
    step: ValidationStep, *, succeeded: bool
) -> ValidationStepResult:
    return ValidationStepResult(
        step=step,
        process=ProcessResult(
            command=("python",),
            exit_code=0 if succeeded else 1,
            stdout="",
            stderr="",
            timed_out=False,
            duration_seconds=0,
        ),
    )


def _write_specifications(root: Path) -> GenerationJobRequest:
    project_path = root / "autoforge.yaml"
    specifications_path = root / "specifications"
    output_path = root / "output"
    specifications_path.mkdir()
    project_path.write_text(
        'spec_version: "1"\n'
        "project:\n"
        "  name: Sample\n"
        "  package_name: sample\n"
        '  version: "0.1.0"\n'
        "application:\n"
        "  modules: [account]\n",
        encoding="utf-8",
    )
    (specifications_path / "account.yaml").write_text(
        'spec_version: "1"\n'
        "module:\n"
        "  name: account\n"
        "  display_name: Account\n"
        "  route_prefix: /api/account\n",
        encoding="utf-8",
    )
    return GenerationJobRequest(
        project_path=project_path,
        specifications_path=specifications_path,
        output_path=output_path,
    )


def _subscribe_lifecycle(bus: EventBus) -> RecordingHandler:
    handler = RecordingHandler()
    for event_type in (
        GenerationJobCreatedEvent,
        GenerationStartedEvent,
        GenerationCompletedEvent,
        ValidationStartedEvent,
        ValidationCompletedEvent,
        ValidationFailedEvent,
    ):
        bus.subscribe(event_type, handler)
    return handler


def test_generation_pipeline_generates_validates_and_persists_job(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        store = InMemoryJobStore()
        bus = EventBus()
        handler = _subscribe_lifecycle(bus)
        pipeline = GenerationJobPipeline(
            job_store=store,
            event_bus=bus,
            validator=SuccessfulValidator(),
        )

        execution = await pipeline.run(
            _write_specifications(tmp_path), job_id="job-001"
        )

        persisted = await store.get("job-001")
        assert persisted == execution.job
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.SUCCEEDED
        assert persisted.manifest is not None
        assert (tmp_path / "output/src/sample/main.py").is_file()
        assert (tmp_path / "output/.autoforge/manifest.json").is_file()
        assert [type(event) for event in handler.events] == [
            GenerationJobCreatedEvent,
            GenerationStartedEvent,
            GenerationCompletedEvent,
            ValidationStartedEvent,
            ValidationCompletedEvent,
        ]
        assert {event.correlation_id for event in handler.events} == {"job-001"}

    asyncio.run(scenario())


def test_generation_pipeline_records_validation_failure(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = InMemoryJobStore()
        bus = EventBus()
        handler = _subscribe_lifecycle(bus)
        pipeline = GenerationJobPipeline(
            job_store=store,
            event_bus=bus,
            validator=FailingValidator(),
        )

        with pytest.raises(PipelineExecutionError) as raised:
            await pipeline.run(
                _write_specifications(tmp_path), job_id="job-failed"
            )

        persisted = await store.get("job-failed")
        assert raised.value.task_name == "validate_generated_project"
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.FAILED
        assert persisted.error == "GenerationValidationError"
        failed = [
            event for event in handler.events if isinstance(event, ValidationFailedEvent)
        ]
        assert len(failed) == 1
        assert failed[0].failed_step == "ruff"

    asyncio.run(scenario())
