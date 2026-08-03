import asyncio

from autoforge.core.job.models import GenerationJob, GenerationJobStatus
from autoforge.core.job.store import DuplicateJobError, JobConcurrencyError


class InMemoryJobStore:
    """Process-local JobStore adapter for CLI execution and deterministic tests."""

    def __init__(self) -> None:
        self._jobs: dict[str, GenerationJob] = {}
        self._lock = asyncio.Lock()

    async def create(self, job: GenerationJob) -> None:
        async with self._lock:
            if job.job_id in self._jobs:
                raise DuplicateJobError(f"GenerationJob already exists: {job.job_id}")
            self._jobs[job.job_id] = job.model_copy(deep=True)

    async def get(self, job_id: str) -> GenerationJob | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            return None if job is None else job.model_copy(deep=True)

    async def replace(
        self,
        job: GenerationJob,
        *,
        expected_status: GenerationJobStatus,
    ) -> None:
        async with self._lock:
            current = self._jobs.get(job.job_id)
            if current is None:
                raise JobConcurrencyError(f"GenerationJob does not exist: {job.job_id}")
            if current.status is not expected_status:
                raise JobConcurrencyError(
                    "GenerationJob status changed concurrently: "
                    f"expected={expected_status}, actual={current.status}"
                )
            self._jobs[job.job_id] = job.model_copy(deep=True)
