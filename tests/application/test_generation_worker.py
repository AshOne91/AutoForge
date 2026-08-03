import asyncio
from datetime import timedelta
from pathlib import Path

import pytest

from autoforge.application.generation import (
    GenerationJobPipeline,
    GenerationSubmissionService,
    GenerationTriggerRequest,
    GenerationWorker,
    GenerationWorkerSettings,
)
from autoforge.core.event import EventBus
from autoforge.core.job import GenerationJobStatus
from autoforge.core.pipeline import PipelineExecutionError
from autoforge.infrastructure.job import InMemoryJobStore
from autoforge.services.validation import (
    ProcessResult,
    ProjectValidationResult,
    ValidationStep,
    ValidationStepResult,
)


class SlowSuccessfulValidator:
    async def validate(self, **_: object) -> ProjectValidationResult:
        await asyncio.sleep(0.7)
        return ProjectValidationResult(
            steps=(
                ValidationStepResult(
                    step=ValidationStep.IMPORT,
                    process=ProcessResult(
                        command=("python",),
                        exit_code=0,
                        stdout="",
                        stderr="",
                        timed_out=False,
                        duration_seconds=0.7,
                    ),
                ),
            )
        )


def _write_specifications(root: Path) -> None:
    modules = root / "spec" / "modules"
    modules.mkdir(parents=True)
    (root / "spec" / "project.yaml").write_text(
        """spec_version: "1"
project:
  name: Sample
  package_name: sample
  version: "0.1.0"
application:
  modules:
    - account
""",
        encoding="utf-8",
    )
    (modules / "account.yaml").write_text(
        """spec_version: "1"
module:
  name: account
  display_name: Account
  route_prefix: /account
""",
        encoding="utf-8",
    )


def test_two_workers_execute_one_submitted_job_with_heartbeat(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        _write_specifications(tmp_path)
        output_root = tmp_path / "output"
        output_root.mkdir()
        store = InMemoryJobStore()
        bus = EventBus()
        submission = GenerationSubmissionService(
            source_root=tmp_path,
            output_root=output_root,
            job_store=store,
            event_bus=bus,
        )
        claimed = await submission.trigger(
            GenerationTriggerRequest(
                project_path="spec/project.yaml",
                specifications_path="spec/modules",
                output_path="generated/service",
            ),
            idempotency_key="delivery-1",
        )
        validator = SlowSuccessfulValidator()

        def worker(worker_id: str) -> GenerationWorker:
            return GenerationWorker(
                settings=GenerationWorkerSettings(
                    worker_id=worker_id,
                    source_root=tmp_path,
                    output_root=output_root,
                    lease_duration=timedelta(milliseconds=500),
                    heartbeat_interval=timedelta(milliseconds=50),
                ),
                job_store=store,
                pipeline=GenerationJobPipeline(
                    job_store=store,
                    event_bus=bus,
                    validator=validator,
                ),
            )

        results = await asyncio.gather(
            worker("worker-1").run_once(),
            worker("worker-2").run_once(),
        )

        executions = [result for result in results if result is not None]
        assert len(executions) == 1
        persisted = await store.get(claimed.job.job_id)
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.SUCCEEDED
        assert (output_root / "generated/service/src/sample/main.py").is_file()

    asyncio.run(scenario())


def test_worker_fails_claimed_job_when_submission_input_disappears(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        _write_specifications(tmp_path)
        output_root = tmp_path / "output"
        output_root.mkdir()
        store = InMemoryJobStore()
        bus = EventBus()
        submission = GenerationSubmissionService(
            source_root=tmp_path,
            output_root=output_root,
            job_store=store,
            event_bus=bus,
        )
        claimed = await submission.trigger(
            GenerationTriggerRequest(
                project_path="spec/project.yaml",
                specifications_path="spec/modules",
                output_path="generated/service",
            ),
            idempotency_key="delivery-1",
        )
        (tmp_path / "spec" / "project.yaml").unlink()
        worker = GenerationWorker(
            settings=GenerationWorkerSettings(
                worker_id="worker-1",
                source_root=tmp_path,
                output_root=output_root,
            ),
            job_store=store,
            pipeline=GenerationJobPipeline(
                job_store=store,
                event_bus=bus,
                validator=SlowSuccessfulValidator(),
            ),
        )

        with pytest.raises(PipelineExecutionError):
            await worker.run_once()

        persisted = await store.get(claimed.job.job_id)
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.FAILED

    asyncio.run(scenario())
