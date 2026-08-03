import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from autoforge.core.job.models import GenerationJob, GenerationJobStatus
from autoforge.core.job.state import GenerationJobStateMachine
from autoforge.core.job.store import (
    DuplicateJobError,
    JobClaim,
    JobConcurrencyError,
    JobLease,
    JobLeaseConflictError,
)


@dataclass(frozen=True, slots=True)
class _LeaseState:
    worker_id: str
    token: str
    expires_at: datetime


class InMemoryJobStore:
    """Process-local JobStore adapter for CLI execution and deterministic tests."""

    def __init__(self) -> None:
        self._jobs: dict[str, GenerationJob] = {}
        self._idempotency_keys: dict[str, str] = {}
        self._leases: dict[str, _LeaseState] = {}
        self._lock = asyncio.Lock()

    async def create(self, job: GenerationJob) -> None:
        async with self._lock:
            if job.job_id in self._jobs:
                raise DuplicateJobError(f"GenerationJob already exists: {job.job_id}")
            self._jobs[job.job_id] = job.model_copy(deep=True)

    async def create_or_get(
        self, job: GenerationJob, *, idempotency_key: str
    ) -> JobClaim:
        if not idempotency_key.strip():
            raise ValueError("idempotency_key must not be empty")
        async with self._lock:
            existing_id = self._idempotency_keys.get(idempotency_key)
            if existing_id is not None:
                return JobClaim(self._jobs[existing_id].model_copy(deep=True), False)
            if job.job_id in self._jobs:
                raise DuplicateJobError(
                    f"GenerationJob already exists: {job.job_id}"
                )
            snapshot = job.model_copy(deep=True)
            self._jobs[job.job_id] = snapshot
            self._idempotency_keys[idempotency_key] = job.job_id
            return JobClaim(snapshot.model_copy(deep=True), True)

    async def get(self, job_id: str) -> GenerationJob | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            return None if job is None else job.model_copy(deep=True)

    async def claim_next(
        self,
        *,
        worker_id: str,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> JobLease | None:
        current_time = _validated_time(now)
        _validate_lease_request(worker_id, lease_duration)
        async with self._lock:
            for job_id, job in self._jobs.items():
                if job.status is not GenerationJobStatus.PENDING:
                    continue
                lease = self._leases.get(job_id)
                if lease is not None and lease.expires_at > current_time:
                    continue
                lease = _LeaseState(
                    worker_id=worker_id,
                    token=str(uuid4()),
                    expires_at=current_time + lease_duration,
                )
                self._leases[job_id] = lease
                return _job_lease(job, lease)
        return None

    async def renew_lease(
        self,
        *,
        job_id: str,
        lease_token: str,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> JobLease:
        current_time = _validated_time(now)
        _validate_lease_request("worker", lease_duration)
        async with self._lock:
            lease = self._leases.get(job_id)
            job = self._jobs.get(job_id)
            if (
                lease is None
                or job is None
                or lease.token != lease_token
                or lease.expires_at <= current_time
                or job.status
                in {GenerationJobStatus.SUCCEEDED, GenerationJobStatus.FAILED}
            ):
                raise JobLeaseConflictError(
                    f"GenerationJob lease is missing, expired, or replaced: {job_id}"
                )
            renewed = _LeaseState(
                worker_id=lease.worker_id,
                token=lease.token,
                expires_at=current_time + lease_duration,
            )
            self._leases[job_id] = renewed
            return _job_lease(job, renewed)

    async def release_lease(self, *, job_id: str, lease_token: str) -> None:
        async with self._lock:
            lease = self._leases.get(job_id)
            if lease is None or lease.token != lease_token:
                raise JobLeaseConflictError(
                    f"GenerationJob lease is missing or replaced: {job_id}"
                )
            del self._leases[job_id]

    async def recover_abandoned(
        self, *, now: datetime | None = None
    ) -> tuple[GenerationJob, ...]:
        current_time = _validated_time(now)
        recovered: list[GenerationJob] = []
        async with self._lock:
            for job_id, lease in tuple(self._leases.items()):
                job = self._jobs[job_id]
                if (
                    lease.expires_at > current_time
                    or job.status
                    not in {
                        GenerationJobStatus.GENERATING,
                        GenerationJobStatus.VALIDATING,
                        GenerationJobStatus.COMMITTING,
                    }
                ):
                    continue
                failed = GenerationJobStateMachine.transition(
                    job,
                    GenerationJobStatus.FAILED,
                    error="JobLeaseExpired",
                )
                self._jobs[job_id] = failed
                del self._leases[job_id]
                recovered.append(failed.model_copy(deep=True))
        return tuple(recovered)

    async def replace(
        self,
        job: GenerationJob,
        *,
        expected_status: GenerationJobStatus,
        lease_token: str | None = None,
    ) -> None:
        current_time = datetime.now(UTC)
        async with self._lock:
            current = self._jobs.get(job.job_id)
            if current is None:
                raise JobConcurrencyError(f"GenerationJob does not exist: {job.job_id}")
            if current.status is not expected_status:
                raise JobConcurrencyError(
                    "GenerationJob status changed concurrently: "
                    f"expected={expected_status}, actual={current.status}"
                )
            lease = self._leases.get(job.job_id)
            if lease is None and lease_token is not None:
                raise JobLeaseConflictError(
                    f"GenerationJob has no active lease: {job.job_id}"
                )
            if lease is not None and (
                lease_token != lease.token or lease.expires_at <= current_time
            ):
                raise JobLeaseConflictError(
                    f"GenerationJob lease is missing, expired, or replaced: {job.job_id}"
                )
            self._jobs[job.job_id] = job.model_copy(deep=True)
            if job.status in {
                GenerationJobStatus.SUCCEEDED,
                GenerationJobStatus.FAILED,
            }:
                self._leases.pop(job.job_id, None)


def _validated_time(value: datetime | None) -> datetime:
    result = value or datetime.now(UTC)
    if result.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    return result


def _validate_lease_request(worker_id: str, duration: timedelta) -> None:
    if not worker_id.strip():
        raise ValueError("worker_id must not be empty")
    if duration <= timedelta(0):
        raise ValueError("lease_duration must be positive")


def _job_lease(job: GenerationJob, lease: _LeaseState) -> JobLease:
    return JobLease(
        job=job.model_copy(deep=True),
        worker_id=lease.worker_id,
        token=lease.token,
        expires_at=lease.expires_at,
    )
