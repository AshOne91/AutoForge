import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from time import monotonic
from typing import Protocol

from autoforge.application.generation.pipeline import (
    GenerationJobExecution,
    GenerationJobPipeline,
    GenerationJobRequest,
)
from autoforge.application.generation.planning import GenerationPlanningService
from autoforge.core.git import GitCheckoutRequest, GitProvider
from autoforge.core.job import (
    GenerationJobStateMachine,
    GenerationJobStatus,
    JobLease,
    JobLeaseConflictError,
    JobStore,
)
from autoforge.core.workspace import Workspace, WorkspaceManager

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
    ) -> None:
        self._settings = settings
        self._job_store = job_store
        self._pipeline = pipeline
        self._git_provider = git_provider
        self._workspace_manager = workspace_manager
        self._planning_service = planning_service
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
            return await self._pipeline.run_claimed(request, lease)

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
