import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path, PurePosixPath
from time import monotonic
from typing import Protocol

from autoforge.application.generation.pipeline import (
    GenerationJobExecution,
    GenerationJobPipeline,
    GenerationJobRequest,
)
from autoforge.application.generation.planning import GenerationPlanningService
from autoforge.core.event import EventBus
from autoforge.core.generation import FileResultStatus
from autoforge.core.git import (
    GitCheckoutRequest,
    GitCommitRequest,
    GitCredentialReference,
    GitProvider,
    GitPushRequest,
)
from autoforge.core.job import (
    GenerationJobStateMachine,
    GenerationJobStatus,
    GitCommitCompletedEvent,
    GitCommitFailedEvent,
    GitCommitStartedEvent,
    GitPushCompletedEvent,
    GitPushFailedEvent,
    GitPushStartedEvent,
    JobLease,
    JobLeaseConflictError,
    JobStore,
)
from autoforge.core.workspace import Workspace, WorkspaceManager
from autoforge.services.generation.manifest_store import MANIFEST_RELATIVE_PATH

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GenerationWorkerSettings:
    worker_id: str
    source_root: Path
    output_root: Path
    lease_duration: timedelta = timedelta(seconds=30)
    heartbeat_interval: timedelta = timedelta(seconds=10)

    def __post_init__(self) -> None:
        if not self.worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if self.lease_duration <= timedelta(0):
            raise ValueError("lease_duration must be positive")
        if self.heartbeat_interval <= timedelta(0):
            raise ValueError("heartbeat_interval must be positive")
        if self.heartbeat_interval >= self.lease_duration:
            raise ValueError("heartbeat_interval must be shorter than lease_duration")


@dataclass(frozen=True, slots=True)
class GenerationGitCommitSettings:
    author_name: str
    author_email: str
    branch_prefix: str = "autoforge"
    commit_message: str = "chore: apply AutoForge generation"
    signing_key: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("author_name", self.author_name),
            ("author_email", self.author_email),
            ("branch_prefix", self.branch_prefix),
            ("commit_message", self.commit_message),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")


@dataclass(frozen=True, slots=True)
class GenerationGitPushSettings:
    remote_name: str = "origin"

    def __post_init__(self) -> None:
        if not self.remote_name.strip():
            raise ValueError("remote_name must not be empty")


@dataclass(frozen=True, slots=True)
class GenerationWorkerResult:
    lease: JobLease
    execution: GenerationJobExecution


@dataclass(frozen=True, slots=True)
class GenerationWorkerLoopSettings:
    idle_poll_interval: timedelta = timedelta(seconds=1)
    error_backoff: timedelta = timedelta(seconds=5)
    abandoned_sweep_interval: timedelta = timedelta(seconds=30)
    shutdown_grace_period: timedelta = timedelta(seconds=30)

    def __post_init__(self) -> None:
        for name, value in (
            ("idle_poll_interval", self.idle_poll_interval),
            ("error_backoff", self.error_backoff),
            ("abandoned_sweep_interval", self.abandoned_sweep_interval),
            ("shutdown_grace_period", self.shutdown_grace_period),
        ):
            if value <= timedelta(0):
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class GenerationWorkerLoopResult:
    completed_jobs: int
    failed_attempts: int
    recovered_jobs: int
    shutdown_timed_out: bool


class GenerationWorkerProtocol(Protocol):
    async def run_once(self) -> GenerationWorkerResult | None: ...


class GenerationWorker:
    def __init__(
        self,
        *,
        settings: GenerationWorkerSettings,
        job_store: JobStore,
        pipeline: GenerationJobPipeline,
        git_provider: GitProvider | None = None,
        workspace_manager: WorkspaceManager | None = None,
        planning_service: GenerationPlanningService | None = None,
        git_commit_settings: GenerationGitCommitSettings | None = None,
        git_push_settings: GenerationGitPushSettings | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._settings = settings
        self._job_store = job_store
        self._pipeline = pipeline
        self._git_provider = git_provider
        self._workspace_manager = workspace_manager
        self._planning_service = planning_service
        self._git_commit_settings = git_commit_settings
        self._git_push_settings = git_push_settings
        self._event_bus = event_bus
        if git_commit_settings is not None and event_bus is None:
            raise ValueError("Git commit execution requires an EventBus")
        if git_push_settings is not None and git_commit_settings is None:
            raise ValueError("Git push execution requires Git commit settings")
        self._source = Workspace(settings.source_root)
        self._output = Workspace(settings.output_root)

    async def run_once(self) -> GenerationWorkerResult | None:
        lease = await self._job_store.claim_next(
            worker_id=self._settings.worker_id,
            lease_duration=self._settings.lease_duration,
        )
        if lease is None:
            return None
        try:
            execution = await self._execute_with_heartbeat(lease)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._fail_active_job(lease, error)
            raise
        return GenerationWorkerResult(lease=lease, execution=execution)

    def _local_request(self, lease: JobLease) -> GenerationJobRequest:
        submission = lease.job.submission
        if submission is None:
            raise ValueError("Claimed GenerationJob has no submission snapshot")
        return GenerationJobRequest(
            project_path=self._source.resolve(submission.project_path),
            specifications_path=self._source.resolve(
                submission.specifications_path
            ),
            output_path=self._output.resolve(submission.output_path),
        )

    async def _execute_with_heartbeat(
        self, lease: JobLease
    ) -> GenerationJobExecution:
        pipeline_task = asyncio.create_task(self._execute_claimed(lease))
        heartbeat_task = asyncio.create_task(self._heartbeat(lease))
        try:
            done, _ = await asyncio.wait(
                (pipeline_task, heartbeat_task),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if pipeline_task in done:
                return await pipeline_task
            error = heartbeat_task.exception()
            if error is None:
                raise RuntimeError("Generation worker heartbeat stopped unexpectedly")
            pipeline_task.cancel()
            with suppress(asyncio.CancelledError):
                await pipeline_task
            raise error
        finally:
            if not pipeline_task.done():
                pipeline_task.cancel()
                with suppress(asyncio.CancelledError):
                    await pipeline_task
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task

    async def _execute_claimed(self, lease: JobLease) -> GenerationJobExecution:
        submission = lease.job.submission
        if submission is None or submission.repository is None:
            return await self._pipeline.run_claimed(
                self._local_request(lease), lease
            )
        if (
            self._git_provider is None
            or self._workspace_manager is None
            or self._planning_service is None
        ):
            raise RuntimeError(
                "Git GenerationJob requires GitProvider, WorkspaceManager and planning service"
            )
        async with self._workspace_manager.create(lease.job.job_id) as workspace:
            repository = submission.repository
            checkout = await self._git_provider.checkout(
                GitCheckoutRequest(
                    repository.repository_url,
                    submission.resolved_commit_sha or repository.revision,
                    destination=repository.destination,
                ),
                workspace=workspace,
            )
            repository_workspace = Workspace(checkout.repository_path)
            request = GenerationJobRequest(
                project_path=repository_workspace.resolve(submission.project_path),
                specifications_path=repository_workspace.resolve(
                    submission.specifications_path
                ),
                output_path=(
                    repository_workspace.root
                    if submission.output_path == "."
                    else repository_workspace.resolve(submission.output_path)
                ),
            )
            if not lease.job.units:
                resolved_submission = submission.model_copy(
                    update={"resolved_commit_sha": checkout.commit_sha}
                )
                planned = await self._planning_service.plan(
                    lease,
                    request,
                    submission=resolved_submission,
                )
                lease = JobLease(
                    job=planned,
                    worker_id=lease.worker_id,
                    token=lease.token,
                    expires_at=lease.expires_at,
                )
            execution = await self._pipeline.run_claimed(
                request,
                lease,
                complete_after_validation=self._git_commit_settings is None,
            )
            if self._git_commit_settings is None:
                return execution
            return await self._commit_validated(
                workspace=workspace,
                repository_destination=repository.destination,
                credential=repository.credential,
                output_path=submission.output_path,
                base_commit_sha=checkout.commit_sha,
                lease=lease,
                execution=execution,
            )

    async def _commit_validated(
        self,
        *,
        workspace: Workspace,
        repository_destination: str,
        credential: GitCredentialReference | None,
        output_path: str,
        base_commit_sha: str,
        lease: JobLease,
        execution: GenerationJobExecution,
    ) -> GenerationJobExecution:
        settings = self._git_commit_settings
        if settings is None or self._git_provider is None:
            raise RuntimeError("Git commit dependencies are not configured")
        manifest = execution.job.manifest
        if manifest is None:
            raise RuntimeError("Validated GenerationJob has no manifest")
        output_prefix = (
            PurePosixPath() if output_path == "." else PurePosixPath(output_path)
        )
        generated_paths = {
            output_prefix / file.relative_path
            for unit in manifest.units
            for file in unit.manifest.files
            if file.status in {FileResultStatus.CREATED, FileResultStatus.CHANGED}
        }
        generated_paths.add(output_prefix / MANIFEST_RELATIVE_PATH)
        branch_name = f"{settings.branch_prefix}/{execution.job.job_id}"
        event_bus = self._event_bus
        if event_bus is None:
            raise RuntimeError("Git commit EventBus is not configured")
        metadata = {
            "job_id": execution.job.job_id,
            "correlation_id": execution.job.job_id,
            "producer": "generation_worker",
        }
        await event_bus.publish(
            GitCommitStartedEvent(
                branch_name=branch_name,
                allowed_path_count=len(generated_paths),
                **metadata,
            )
        )
        try:
            result = await self._git_provider.commit_validated(
                GitCommitRequest(
                    expected_base_sha=base_commit_sha,
                    branch_name=branch_name,
                    message=settings.commit_message,
                    author_name=settings.author_name,
                    author_email=settings.author_email,
                    allowed_paths=tuple(sorted(generated_paths)),
                    repository_destination=repository_destination,
                    signing_key=settings.signing_key,
                ),
                workspace=workspace,
            )
        except Exception as error:
            failed = GenerationJobStateMachine.transition(
                execution.job,
                GenerationJobStatus.FAILED,
                error=type(error).__name__,
            )
            await self._job_store.replace(
                failed,
                expected_status=GenerationJobStatus.COMMITTING,
                lease_token=lease.token,
            )
            await event_bus.publish(
                GitCommitFailedEvent(error_type=type(error).__name__, **metadata)
            )
            raise
        completed_status = (
            GenerationJobStatus.PUSHING
            if self._git_push_settings is not None and result.commit_created
            else GenerationJobStatus.SUCCEEDED
        )
        completed = GenerationJobStateMachine.transition(
            execution.job,
            completed_status,
            git_commit=result,
        )
        await self._job_store.replace(
            completed,
            expected_status=GenerationJobStatus.COMMITTING,
            lease_token=lease.token,
        )
        await event_bus.publish(
            GitCommitCompletedEvent(
                commit_sha=result.commit_sha,
                branch_name=result.branch_name,
                changed_paths=tuple(
                    path.as_posix() for path in result.changed_paths
                ),
                commit_created=result.commit_created,
                **metadata,
            )
        )
        committed_execution = GenerationJobExecution(
            job=completed,
            pipeline_result=execution.pipeline_result,
        )
        if completed_status is GenerationJobStatus.PUSHING:
            return await self._push_validated(
                workspace=workspace,
                repository_destination=repository_destination,
                credential=credential,
                lease=lease,
                execution=committed_execution,
            )
        return GenerationJobExecution(
            job=completed,
            pipeline_result=execution.pipeline_result,
        )

    async def _push_validated(
        self,
        *,
        workspace: Workspace,
        repository_destination: str,
        credential: GitCredentialReference | None,
        lease: JobLease,
        execution: GenerationJobExecution,
    ) -> GenerationJobExecution:
        settings = self._git_push_settings
        commit = execution.job.git_commit
        event_bus = self._event_bus
        if (
            settings is None
            or commit is None
            or commit.branch_name is None
            or self._git_provider is None
            or event_bus is None
        ):
            raise RuntimeError("Git push dependencies are not configured")
        metadata = {
            "job_id": execution.job.job_id,
            "correlation_id": execution.job.job_id,
            "producer": "generation_worker",
        }
        await event_bus.publish(
            GitPushStartedEvent(
                commit_sha=commit.commit_sha,
                branch_name=commit.branch_name,
                remote_name=settings.remote_name,
                **metadata,
            )
        )
        try:
            result = await self._git_provider.push_validated(
                GitPushRequest(
                    expected_commit_sha=commit.commit_sha,
                    branch_name=commit.branch_name,
                    repository_destination=repository_destination,
                    remote_name=settings.remote_name,
                    credential=credential,
                ),
                workspace=workspace,
            )
        except Exception as error:
            failed = GenerationJobStateMachine.transition(
                execution.job,
                GenerationJobStatus.FAILED,
                error=type(error).__name__,
            )
            await self._job_store.replace(
                failed,
                expected_status=GenerationJobStatus.PUSHING,
                lease_token=lease.token,
            )
            await event_bus.publish(
                GitPushFailedEvent(error_type=type(error).__name__, **metadata)
            )
            raise
        succeeded = GenerationJobStateMachine.transition(
            execution.job,
            GenerationJobStatus.SUCCEEDED,
            git_push=result,
        )
        await self._job_store.replace(
            succeeded,
            expected_status=GenerationJobStatus.PUSHING,
            lease_token=lease.token,
        )
        await event_bus.publish(
            GitPushCompletedEvent(
                commit_sha=result.commit_sha,
                branch_name=result.branch_name,
                remote_url=result.remote_url,
                pushed=result.pushed,
                **metadata,
            )
        )
        return GenerationJobExecution(
            job=succeeded,
            pipeline_result=execution.pipeline_result,
        )

    async def _heartbeat(self, lease: JobLease) -> None:
        while True:
            await asyncio.sleep(self._settings.heartbeat_interval.total_seconds())
            try:
                await self._job_store.renew_lease(
                    job_id=lease.job.job_id,
                    lease_token=lease.token,
                    lease_duration=self._settings.lease_duration,
                )
            except JobLeaseConflictError:
                current = await self._job_store.get(lease.job.job_id)
                if current is not None and current.status in {
                    GenerationJobStatus.SUCCEEDED,
                    GenerationJobStatus.FAILED,
                }:
                    return
                raise

    async def _fail_active_job(self, lease: JobLease, error: Exception) -> None:
        current = await self._job_store.get(lease.job.job_id)
        if current is None or current.status in {
            GenerationJobStatus.SUCCEEDED,
            GenerationJobStatus.FAILED,
        }:
            return
        failed = GenerationJobStateMachine.transition(
            current,
            GenerationJobStatus.FAILED,
            error=type(error).__name__,
        )
        try:
            await self._job_store.replace(
                failed,
                expected_status=current.status,
                lease_token=lease.token,
            )
        except JobLeaseConflictError:
            return


class GenerationWorkerLoop:
    def __init__(
        self,
        *,
        worker: GenerationWorkerProtocol,
        job_store: JobStore,
        settings: GenerationWorkerLoopSettings | None = None,
    ) -> None:
        self._worker = worker
        self._job_store = job_store
        self._settings = settings or GenerationWorkerLoopSettings()

    async def run(self, stop_event: asyncio.Event) -> GenerationWorkerLoopResult:
        completed_jobs = 0
        failed_attempts = 0
        recovered_jobs = 0
        shutdown_timed_out = False
        next_sweep_at = 0.0

        while not stop_event.is_set():
            if monotonic() >= next_sweep_at:
                try:
                    recovered_jobs += len(
                        await self._job_store.recover_abandoned()
                    )
                except Exception:
                    failed_attempts += 1
                    logger.exception("Generation worker abandoned sweep failed")
                    if await _wait_for_stop(
                        stop_event, self._settings.error_backoff
                    ):
                        break
                next_sweep_at = (
                    monotonic()
                    + self._settings.abandoned_sweep_interval.total_seconds()
                )

            work_task = asyncio.create_task(self._worker.run_once())
            stop_task = asyncio.create_task(stop_event.wait())
            done, _ = await asyncio.wait(
                (work_task, stop_task), return_when=asyncio.FIRST_COMPLETED
            )

            if stop_task in done:
                if not work_task.done():
                    try:
                        result = await asyncio.wait_for(
                            asyncio.shield(work_task),
                            timeout=self._settings.shutdown_grace_period.total_seconds(),
                        )
                        if result is not None:
                            completed_jobs += 1
                    except TimeoutError:
                        shutdown_timed_out = True
                        work_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await work_task
                    except Exception:
                        failed_attempts += 1
                        logger.exception(
                            "Generation worker failed during graceful shutdown"
                        )
                elif not work_task.cancelled() and work_task.exception() is not None:
                    failed_attempts += 1
                    error = work_task.exception()
                    assert error is not None
                    logger.error(
                        "Generation worker failed as shutdown was requested",
                        exc_info=(type(error), error, error.__traceback__),
                    )
                elif not work_task.cancelled() and work_task.result() is not None:
                    completed_jobs += 1
                break

            stop_task.cancel()
            with suppress(asyncio.CancelledError):
                await stop_task
            try:
                result = await work_task
            except Exception:
                failed_attempts += 1
                logger.exception("Generation worker attempt failed")
                if await _wait_for_stop(stop_event, self._settings.error_backoff):
                    break
                continue
            if result is not None:
                completed_jobs += 1
                continue
            if await _wait_for_stop(
                stop_event, self._settings.idle_poll_interval
            ):
                break

        return GenerationWorkerLoopResult(
            completed_jobs=completed_jobs,
            failed_attempts=failed_attempts,
            recovered_jobs=recovered_jobs,
            shutdown_timed_out=shutdown_timed_out,
        )


async def _wait_for_stop(
    stop_event: asyncio.Event, duration: timedelta
) -> bool:
    try:
        await asyncio.wait_for(
            stop_event.wait(), timeout=duration.total_seconds()
        )
    except TimeoutError:
        return False
    return True
