import asyncio
from datetime import timedelta
from pathlib import Path

import pytest

from autoforge.application.generation import (
    GenerationJobPipeline,
    GenerationPlanningService,
    GenerationSubmissionService,
    GenerationTriggerRequest,
    GenerationWorker,
    GenerationWorkerSettings,
)
from autoforge.core.event import EventBus
from autoforge.core.git import GitCheckoutPolicy
from autoforge.core.job import GenerationJobStatus
from autoforge.core.pipeline import PipelineExecutionError
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.git import SubprocessGitProvider
from autoforge.infrastructure.job import InMemoryJobStore
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.infrastructure.workspace import IsolatedWorkspaceManager
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


class RecordingSuccessfulValidator(SlowSuccessfulValidator):
    def __init__(self) -> None:
        self.workspace_root: Path | None = None

    async def validate(
        self, *, package_name: str, workspace: Workspace
    ) -> ProjectValidationResult:
        del package_name
        self.workspace_root = workspace.root
        return await super().validate()


class FailingValidator:
    async def validate(self, **_: object) -> ProjectValidationResult:
        raise RuntimeError("validation failed")


async def _git(cwd: Path, *arguments: str) -> str:
    result = await AsyncioProcessRunner().run(
        ("git", *arguments), cwd=cwd, timeout_seconds=10
    )
    assert result.succeeded, result.stderr or result.error
    return result.stdout.strip()


async def _create_source_repository(root: Path) -> tuple[Path, str]:
    repository = root / "sources" / "sample"
    repository.mkdir(parents=True)
    _write_specifications(repository)
    await _git(repository, "init")
    await _git(repository, "config", "user.name", "AutoForge Test")
    await _git(repository, "config", "user.email", "autoforge@example.invalid")
    await _git(repository, "add", ".")
    await _git(repository, "commit", "-m", "initial")
    return repository, await _git(repository, "rev-parse", "HEAD")


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


def test_worker_plans_and_generates_from_isolated_git_checkout(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        source, commit_sha = await _create_source_repository(tmp_path)
        workspaces = tmp_path / "workspaces"
        store = InMemoryJobStore()
        bus = EventBus()
        submitted = await GenerationSubmissionService(
            source_root=tmp_path,
            output_root=tmp_path,
            job_store=store,
            event_bus=bus,
        ).trigger(
            GenerationTriggerRequest(
                project_path="spec/project.yaml",
                specifications_path="spec/modules",
                output_path=".",
                repository_url=str(source),
                revision=commit_sha,
            ),
            idempotency_key="delivery-git-success",
        )
        validator = RecordingSuccessfulValidator()
        worker = GenerationWorker(
            settings=GenerationWorkerSettings(
                worker_id="worker-1",
                source_root=tmp_path,
                output_root=tmp_path,
            ),
            job_store=store,
            pipeline=GenerationJobPipeline(
                job_store=store,
                event_bus=bus,
                validator=validator,
            ),
            git_provider=SubprocessGitProvider(
                policy=GitCheckoutPolicy(
                    allowed_hosts=frozenset(),
                    allowed_local_roots=(tmp_path / "sources",),
                )
            ),
            workspace_manager=IsolatedWorkspaceManager(workspaces),
            planning_service=GenerationPlanningService(
                job_store=store, event_bus=bus
            ),
        )

        await worker.run_once()

        persisted = await store.get(submitted.job.job_id)
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.SUCCEEDED
        assert persisted.units
        assert persisted.submission is not None
        assert persisted.submission.resolved_commit_sha == commit_sha
        assert validator.workspace_root is not None
        assert not validator.workspace_root.exists()
        assert list(workspaces.iterdir()) == []
        assert not (source / "src" / "sample").exists()
        assert await _git(source, "status", "--porcelain") == ""

    asyncio.run(scenario())


def test_worker_preserves_failed_git_workspace_without_touching_source(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        source, commit_sha = await _create_source_repository(tmp_path)
        workspaces = tmp_path / "workspaces"
        store = InMemoryJobStore()
        bus = EventBus()
        submitted = await GenerationSubmissionService(
            source_root=tmp_path,
            output_root=tmp_path,
            job_store=store,
            event_bus=bus,
        ).trigger(
            GenerationTriggerRequest(
                project_path="spec/project.yaml",
                specifications_path="spec/modules",
                output_path=".",
                repository_url=str(source),
                revision=commit_sha,
            ),
            idempotency_key="delivery-git-failure",
        )
        worker = GenerationWorker(
            settings=GenerationWorkerSettings(
                worker_id="worker-1",
                source_root=tmp_path,
                output_root=tmp_path,
            ),
            job_store=store,
            pipeline=GenerationJobPipeline(
                job_store=store,
                event_bus=bus,
                validator=FailingValidator(),
            ),
            git_provider=SubprocessGitProvider(
                policy=GitCheckoutPolicy(
                    allowed_hosts=frozenset(),
                    allowed_local_roots=(tmp_path / "sources",),
                )
            ),
            workspace_manager=IsolatedWorkspaceManager(
                workspaces, preserve_on_error=True
            ),
            planning_service=GenerationPlanningService(
                job_store=store, event_bus=bus
            ),
        )

        with pytest.raises(PipelineExecutionError):
            await worker.run_once()

        persisted = await store.get(submitted.job.job_id)
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.FAILED
        preserved = list(workspaces.iterdir())
        assert len(preserved) == 1
        assert (preserved[0] / "repository" / ".git").is_dir()
        assert (preserved[0] / "repository" / "src" / "sample").is_dir()
        assert not (source / "src" / "sample").exists()
        assert await _git(source, "status", "--porcelain") == ""

    asyncio.run(scenario())
