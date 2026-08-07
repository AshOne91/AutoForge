import asyncio
from datetime import timedelta
from pathlib import Path

import pytest

from autoforge.application.generation import (
    GenerationGitCommitSettings,
    GenerationGitPushSettings,
    GenerationJobPipeline,
    GenerationPlanningService,
    GenerationPullRequestSettings,
    GenerationSubmissionService,
    GenerationTriggerRequest,
    GenerationWorker,
    GenerationWorkerSettings,
)
from autoforge.core.event import Event, EventBus, EventHandler
from autoforge.core.git import (
    GitCheckoutPolicy,
    GitPullRequestRequest,
    GitPullRequestResult,
    GitPushRequest,
    GitPushResult,
)
from autoforge.core.job import (
    GenerationJobStatus,
    GitCommitCompletedEvent,
    GitCommitFailedEvent,
    GitCommitStartedEvent,
    GitPushCompletedEvent,
    GitPushFailedEvent,
    GitPushStartedEvent,
    PullRequestCompletedEvent,
    PullRequestFailedEvent,
    PullRequestStartedEvent,
)
from autoforge.core.pipeline import PipelineExecutionError
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.git import GitProviderError, SubprocessGitProvider
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


class RecordingHandler(EventHandler):
    def __init__(self) -> None:
        self.events: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.events.append(event)


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


class UnexpectedChangeValidator(SlowSuccessfulValidator):
    async def validate(
        self, *, package_name: str, workspace: Workspace
    ) -> ProjectValidationResult:
        del package_name
        (workspace.root / "unexpected.txt").write_text(
            "not generated\n", encoding="utf-8"
        )
        return await super().validate()


class FailingPushProvider(SubprocessGitProvider):
    async def push_validated(
        self, request: GitPushRequest, *, workspace: Workspace
    ) -> GitPushResult:
        del request, workspace
        raise GitProviderError("simulated push failure")


class RecordingPullRequestProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.requests: list[GitPullRequestRequest] = []

    async def create_or_get(
        self, request: GitPullRequestRequest
    ) -> GitPullRequestResult:
        self.requests.append(request)
        if self._fail:
            raise RuntimeError("simulated Pull Request failure")
        return GitPullRequestResult(
            pull_request_id="42",
            url="https://github.com/example/repository/pull/42",
            head_sha=request.expected_head_sha,
            head_branch=request.head_branch,
            base_branch=request.base_branch,
            created=True,
        )


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


async def _create_bare_source_repository(root: Path) -> tuple[Path, str]:
    source, commit_sha = await _create_source_repository(root)
    remote = root / "remotes" / "source.git"
    remote.parent.mkdir()
    remote.mkdir()
    await _git(remote, "init", "--bare")
    await _git(source, "remote", "add", "generated", str(remote))
    await _git(source, "push", "generated", "HEAD:refs/heads/main")
    return remote, commit_sha


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


def test_worker_commits_pushes_and_opens_pull_request(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        remote, commit_sha = await _create_bare_source_repository(tmp_path)
        workspaces = tmp_path / "workspaces"
        store = InMemoryJobStore()
        bus = EventBus()
        commit_events = RecordingHandler()
        bus.subscribe(GitCommitStartedEvent, commit_events)
        bus.subscribe(GitCommitCompletedEvent, commit_events)
        bus.subscribe(GitPushStartedEvent, commit_events)
        bus.subscribe(GitPushCompletedEvent, commit_events)
        bus.subscribe(PullRequestStartedEvent, commit_events)
        bus.subscribe(PullRequestCompletedEvent, commit_events)
        pull_requests = RecordingPullRequestProvider()
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
                repository_url=str(remote),
                revision=commit_sha,
            ),
            idempotency_key="delivery-git-commit",
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
                validator=SlowSuccessfulValidator(),
            ),
            git_provider=SubprocessGitProvider(
                policy=GitCheckoutPolicy(
                    allowed_hosts=frozenset(),
                    allowed_local_roots=(tmp_path / "remotes",),
                )
            ),
            workspace_manager=IsolatedWorkspaceManager(workspaces),
            planning_service=GenerationPlanningService(
                job_store=store, event_bus=bus
            ),
            git_commit_settings=GenerationGitCommitSettings(
                author_name="AutoForge",
                author_email="autoforge@example.invalid",
            ),
            git_push_settings=GenerationGitPushSettings(),
            pull_request_provider=pull_requests,
            pull_request_settings=GenerationPullRequestSettings(),
            event_bus=bus,
        )

        result = await worker.run_once()

        assert result is not None
        persisted = await store.get(submitted.job.job_id)
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.SUCCEEDED
        assert persisted.git_commit is not None
        assert persisted.git_commit.commit_created is True
        assert persisted.git_commit.branch_name == (
            f"autoforge/{submitted.job.job_id}"
        )
        assert persisted.git_commit.commit_sha != commit_sha
        assert persisted.git_push is not None
        assert persisted.git_push.pushed is True
        assert persisted.git_push.commit_sha == persisted.git_commit.commit_sha
        assert persisted.git_pull_request is not None
        assert persisted.git_pull_request.pull_request_id == "42"
        assert persisted.git_pull_request.head_sha == persisted.git_push.commit_sha
        assert len(pull_requests.requests) == 1
        assert pull_requests.requests[0].base_branch == "main"
        changed = {path.as_posix() for path in persisted.git_commit.changed_paths}
        assert ".autoforge/manifest.json" in changed
        assert "src/sample/main.py" in changed
        assert list(workspaces.iterdir()) == []
        assert await _git(remote, "rev-parse", "refs/heads/main") == commit_sha
        assert await _git(
            remote,
            "rev-parse",
            f"refs/heads/autoforge/{submitted.job.job_id}",
        ) == persisted.git_commit.commit_sha
        assert [type(event) for event in commit_events.events] == [
            GitCommitStartedEvent,
            GitCommitCompletedEvent,
            GitPushStartedEvent,
            GitPushCompletedEvent,
            PullRequestStartedEvent,
            PullRequestCompletedEvent,
        ]

    asyncio.run(scenario())


def test_worker_fails_committing_job_on_change_outside_manifest_allowlist(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        source, commit_sha = await _create_source_repository(tmp_path)
        workspaces = tmp_path / "workspaces"
        store = InMemoryJobStore()
        bus = EventBus()
        commit_events = RecordingHandler()
        bus.subscribe(GitCommitStartedEvent, commit_events)
        bus.subscribe(GitCommitFailedEvent, commit_events)
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
            idempotency_key="delivery-git-unexpected-change",
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
                validator=UnexpectedChangeValidator(),
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
            git_commit_settings=GenerationGitCommitSettings(
                author_name="AutoForge",
                author_email="autoforge@example.invalid",
            ),
            event_bus=bus,
        )

        with pytest.raises(GitProviderError, match="outside the allowlist"):
            await worker.run_once()

        persisted = await store.get(submitted.job.job_id)
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.FAILED
        assert persisted.error == "GitProviderError"
        preserved = list(workspaces.iterdir())
        assert len(preserved) == 1
        repository = preserved[0] / "repository"
        assert (repository / "unexpected.txt").is_file()
        assert await _git(repository, "branch", "--show-current") == ""
        assert await _git(repository, "rev-parse", "HEAD") == commit_sha
        assert await _git(source, "status", "--porcelain") == ""
        assert [type(event) for event in commit_events.events] == [
            GitCommitStartedEvent,
            GitCommitFailedEvent,
        ]

    asyncio.run(scenario())


def test_worker_persists_failed_job_and_event_when_push_fails(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        remote, commit_sha = await _create_bare_source_repository(tmp_path)
        workspaces = tmp_path / "workspaces"
        store = InMemoryJobStore()
        bus = EventBus()
        push_events = RecordingHandler()
        bus.subscribe(GitPushStartedEvent, push_events)
        bus.subscribe(GitPushFailedEvent, push_events)
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
                repository_url=str(remote),
                revision=commit_sha,
            ),
            idempotency_key="delivery-git-push-failure",
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
                validator=SlowSuccessfulValidator(),
            ),
            git_provider=FailingPushProvider(
                policy=GitCheckoutPolicy(
                    allowed_hosts=frozenset(),
                    allowed_local_roots=(tmp_path / "remotes",),
                )
            ),
            workspace_manager=IsolatedWorkspaceManager(
                workspaces, preserve_on_error=True
            ),
            planning_service=GenerationPlanningService(
                job_store=store, event_bus=bus
            ),
            git_commit_settings=GenerationGitCommitSettings(
                author_name="AutoForge",
                author_email="autoforge@example.invalid",
            ),
            git_push_settings=GenerationGitPushSettings(),
            event_bus=bus,
        )

        with pytest.raises(GitProviderError, match="simulated push failure"):
            await worker.run_once()

        persisted = await store.get(submitted.job.job_id)
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.FAILED
        assert persisted.error == "GitProviderError"
        assert persisted.git_commit is not None
        assert persisted.git_push is None
        assert [type(event) for event in push_events.events] == [
            GitPushStartedEvent,
            GitPushFailedEvent,
        ]
        assert await _git(remote, "rev-parse", "refs/heads/main") == commit_sha
        assert len(list(workspaces.iterdir())) == 1

    asyncio.run(scenario())


def test_worker_persists_failed_job_and_event_when_pull_request_fails(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        remote, commit_sha = await _create_bare_source_repository(tmp_path)
        workspaces = tmp_path / "workspaces"
        store = InMemoryJobStore()
        bus = EventBus()
        pull_request_events = RecordingHandler()
        bus.subscribe(PullRequestStartedEvent, pull_request_events)
        bus.subscribe(PullRequestFailedEvent, pull_request_events)
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
                repository_url=str(remote),
                revision=commit_sha,
            ),
            idempotency_key="delivery-pull-request-failure",
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
                validator=SlowSuccessfulValidator(),
            ),
            git_provider=SubprocessGitProvider(
                policy=GitCheckoutPolicy(
                    allowed_hosts=frozenset(),
                    allowed_local_roots=(tmp_path / "remotes",),
                )
            ),
            workspace_manager=IsolatedWorkspaceManager(
                workspaces, preserve_on_error=True
            ),
            planning_service=GenerationPlanningService(
                job_store=store, event_bus=bus
            ),
            git_commit_settings=GenerationGitCommitSettings(
                author_name="AutoForge",
                author_email="autoforge@example.invalid",
            ),
            git_push_settings=GenerationGitPushSettings(),
            pull_request_provider=RecordingPullRequestProvider(fail=True),
            pull_request_settings=GenerationPullRequestSettings(),
            event_bus=bus,
        )

        with pytest.raises(RuntimeError, match="simulated Pull Request failure"):
            await worker.run_once()

        persisted = await store.get(submitted.job.job_id)
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.FAILED
        assert persisted.error == "RuntimeError"
        assert persisted.git_commit is not None
        assert persisted.git_push is not None
        assert persisted.git_pull_request is None
        assert [type(event) for event in pull_request_events.events] == [
            PullRequestStartedEvent,
            PullRequestFailedEvent,
        ]
        assert len(list(workspaces.iterdir())) == 1

    asyncio.run(scenario())
