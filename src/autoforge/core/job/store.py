from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from autoforge.core.job.models import GenerationJob, GenerationJobStatus


class DuplicateJobError(RuntimeError):
    pass


class JobConcurrencyError(RuntimeError):
    pass


class JobLeaseConflictError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class JobClaim:
    job: GenerationJob
    created: bool


@dataclass(frozen=True, slots=True)
class JobLease:
    job: GenerationJob
    worker_id: str
    token: str
    expires_at: datetime


class JobStore(Protocol):
    async def create(self, job: GenerationJob) -> None: ...

    async def create_or_get(
        self, job: GenerationJob, *, idempotency_key: str
    ) -> JobClaim: ...

    async def get(self, job_id: str) -> GenerationJob | None: ...

    async def claim_next(
        self,
        *,
        worker_id: str,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> JobLease | None: ...

    async def renew_lease(
        self,
        *,
        job_id: str,
        lease_token: str,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> JobLease: ...

    async def release_lease(self, *, job_id: str, lease_token: str) -> None: ...

    async def recover_abandoned(
        self, *, now: datetime | None = None
    ) -> tuple[GenerationJob, ...]: ...

    async def replace(
        self,
        job: GenerationJob,
        *,
        expected_status: GenerationJobStatus,
        lease_token: str | None = None,
    ) -> None: ...
