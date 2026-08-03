from typing import Protocol

from autoforge.core.job.models import GenerationJob, GenerationJobStatus


class DuplicateJobError(RuntimeError):
    pass


class JobConcurrencyError(RuntimeError):
    pass


class JobStore(Protocol):
    async def create(self, job: GenerationJob) -> None: ...

    async def get(self, job_id: str) -> GenerationJob | None: ...

    async def replace(
        self,
        job: GenerationJob,
        *,
        expected_status: GenerationJobStatus,
    ) -> None: ...
