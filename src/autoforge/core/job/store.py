from dataclasses import dataclass
from typing import Protocol

from autoforge.core.job.models import GenerationJob, GenerationJobStatus


class DuplicateJobError(RuntimeError):
    pass


class JobConcurrencyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class JobClaim:
    job: GenerationJob
    created: bool


class JobStore(Protocol):
    async def create(self, job: GenerationJob) -> None: ...

    async def create_or_get(
        self, job: GenerationJob, *, idempotency_key: str
    ) -> JobClaim: ...

    async def get(self, job_id: str) -> GenerationJob | None: ...

    async def replace(
        self,
        job: GenerationJob,
        *,
        expected_status: GenerationJobStatus,
    ) -> None: ...
