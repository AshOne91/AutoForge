import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from autoforge.application.generation.pipeline import (
    GenerationJobExecution,
    GenerationJobPipeline,
    GenerationJobRequest,
)
from autoforge.core.job import (
    GenerationJobStateMachine,
    GenerationJobStatus,
    JobLease,
    JobLeaseConflictError,
    JobStore,
)
from autoforge.core.workspace import Workspace


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


class GenerationWorker:
    def __init__(
        self,
        *,
        settings: GenerationWorkerSettings,
        job_store: JobStore,
        pipeline: GenerationJobPipeline,
    ) -> None:
        self._settings = settings
        self._job_store = job_store
        self._pipeline = pipeline
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
            request = self._request(lease)
            execution = await self._execute_with_heartbeat(request, lease)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._fail_active_job(lease, error)
            raise
        return GenerationWorkerResult(lease=lease, execution=execution)

    def _request(self, lease: JobLease) -> GenerationJobRequest:
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
        self, request: GenerationJobRequest, lease: JobLease
    ) -> GenerationJobExecution:
        pipeline_task = asyncio.create_task(
            self._pipeline.run_claimed(request, lease)
        )
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
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task

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
