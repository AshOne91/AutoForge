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
    def __init__(self, package_name: str = "sample") -> None:
        self._package_name = package_name

    async def validate(
        self, *, package_name: str, workspace: Workspace
    ) -> ProjectValidationResult:
        assert package_name == self._package_name
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


def _write_identity_account_specifications(root: Path) -> GenerationJobRequest:
    request = _write_specifications(root)
    request.project_path.write_text(
        'spec_version: "1"\n'
        "project:\n"
        "  name: Sample\n"
        "  package_name: sample\n"
        '  version: "0.1.0"\n'
        "application:\n"
        "  modules: [identity, account]\n",
        encoding="utf-8",
    )
    (request.specifications_path / "identity.yaml").write_text(
        'spec_version: "1"\n'
        "module:\n"
        "  name: identity\n"
        "  display_name: Identity\n"
        "  route_prefix: /api/identity\n",
        encoding="utf-8",
    )
    return request


def _write_rag_project_specification(
    root: Path, *, enabled: bool, host_port_base: int = 49400
) -> GenerationJobRequest:
    project_path = root / "autoforge.yaml"
    specifications_path = root / "specifications"
    output_path = root / "output"
    specifications_path.mkdir(exist_ok=True)
    project_path.write_text(
        'spec_version: "1"\n'
        "tooling:\n"
        "  rag:\n"
        f"    enabled: {str(enabled).lower()}\n"
        f"    host_port_base: {host_port_base}\n"
        "project:\n"
        "  name: Sample\n"
        "  package_name: sample\n"
        '  version: "0.1.0"\n'
        "application: {}\n",
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


def test_generation_pipeline_retains_opt_in_generated_files_when_disabled(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        pipeline = GenerationJobPipeline(
            job_store=InMemoryJobStore(),
            event_bus=EventBus(),
            validator=SuccessfulValidator(),
        )

        await pipeline.run(
            _write_rag_project_specification(tmp_path, enabled=True),
            job_id="job-rag-enabled",
        )
        await pipeline.run(
            _write_rag_project_specification(tmp_path, enabled=False),
            job_id="job-rag-disabled",
        )
        execution = await pipeline.run(
            _write_rag_project_specification(
                tmp_path, enabled=True, host_port_base=49500
            ),
            job_id="job-rag-reenabled",
        )

        assert execution.job.status is GenerationJobStatus.SUCCEEDED
        assert (
            "QDRANT_HTTP_PORT=49550"
            in (tmp_path / "output/deploy/rag/.env.example").read_text()
        )

    asyncio.run(scenario())


def test_generation_pipeline_composes_all_declared_modules(tmp_path: Path) -> None:
    async def scenario() -> None:
        pipeline = GenerationJobPipeline(
            job_store=InMemoryJobStore(),
            event_bus=EventBus(),
            validator=SuccessfulValidator(),
        )

        execution = await pipeline.run(
            _write_identity_account_specifications(tmp_path),
            job_id="job-identity-account",
        )

        assert execution.job.manifest is not None
        assert {unit.unit_id for unit in execution.job.manifest.units} == {
            "project",
            "module:identity",
            "module:account",
        }
        assert (tmp_path / "output/src/sample/modules/identity/generated/router.py").is_file()
        assert (tmp_path / "output/src/sample/modules/account/generated/router.py").is_file()

    asyncio.run(scenario())


def test_generation_pipeline_generates_identity_session_profile_blueprint(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        blueprint = (
            Path(__file__).parents[2] / "blueprints" / "identity_session_profile"
        )
        pipeline = GenerationJobPipeline(
            job_store=InMemoryJobStore(),
            event_bus=EventBus(),
            validator=SuccessfulValidator("base_server"),
        )

        execution = await pipeline.run(
            GenerationJobRequest(
                project_path=blueprint / "autoforge.yaml",
                specifications_path=blueprint / "specifications",
                output_path=tmp_path / "output",
            ),
            job_id="job-identity-session-profile",
        )

        assert execution.job.manifest is not None
        assert {unit.unit_id for unit in execution.job.manifest.units} == {
            "project",
            "module:identity",
            "module:account",
        }
        assert (
            tmp_path
            / "output/src/base_server/modules/identity/handlers.py"
        ).is_file()
        assert (
            tmp_path
            / "output/src/base_server/modules/account/handlers.py"
        ).is_file()
        assert (
            tmp_path / "output/environment/compose.integration.yml"
        ).is_file()
        compose = (
            tmp_path / "output/environment/compose.integration.yml"
        ).read_text(encoding="utf-8")
        assert "postgres:" in compose
        assert "redis-7000:" in compose
        assert "application:" in compose
        assert "migrate:" in compose
        assert "DURABLE_JOB_API_TOKEN:" not in compose
        assert (tmp_path / "output/Dockerfile").is_file()

    asyncio.run(scenario())


def test_generation_pipeline_generates_scheduled_ingestion_blueprint(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        blueprint = Path(__file__).parents[2] / "blueprints" / "scheduled_ingestion"
        pipeline = GenerationJobPipeline(
            job_store=InMemoryJobStore(),
            event_bus=EventBus(),
            validator=SuccessfulValidator("ingestion_server"),
        )

        execution = await pipeline.run(
            GenerationJobRequest(
                project_path=blueprint / "autoforge.yaml",
                specifications_path=blueprint / "specifications",
                output_path=tmp_path / "output",
            ),
            job_id="job-scheduled-ingestion",
        )

        assert execution.job.manifest is not None
        assert [unit.unit_id for unit in execution.job.manifest.units] == ["project"]
        assert (
            tmp_path
            / "output/src/ingestion_server/application/durable_job_handler.py"
        ).is_file()
        assert (tmp_path / "output/airflow/dags/scheduled_ingestion.py").is_file()
        assert (tmp_path / "output/scripts/run_durable_job_worker.py").is_file()
        assert (tmp_path / "output/deploy/rag/compose.rag.yaml").is_file()
        assert (tmp_path / "output/deploy/storage/compose.storage.yaml").is_file()

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
