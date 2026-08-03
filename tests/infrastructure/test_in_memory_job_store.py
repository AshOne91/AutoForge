import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from autoforge.core.generation import content_hash
from autoforge.core.job import (
    DuplicateJobError,
    GenerationJob,
    GenerationJobStateMachine,
    GenerationJobStatus,
    GenerationUnit,
    GenerationUnitKind,
    JobConcurrencyError,
    JobLeaseConflictError,
)
from autoforge.infrastructure.job import InMemoryJobStore


def _job() -> GenerationJob:
    return GenerationJob(
        job_id="job-001",
        units=[
            GenerationUnit(
                unit_id="project",
                kind=GenerationUnitKind.PROJECT,
                specification_version="1",
                specification_hash=content_hash("project"),
            )
        ],
    )


def test_store_returns_snapshots_and_compare_and_swaps_status() -> None:
    async def scenario() -> None:
        store = InMemoryJobStore()
        pending = _job()
        await store.create(pending)
        loaded = await store.get(pending.job_id)
        assert loaded is not None
        generating = GenerationJobStateMachine.transition(
            loaded, GenerationJobStatus.GENERATING
        )

        await store.replace(
            generating, expected_status=GenerationJobStatus.PENDING
        )

        persisted = await store.get(pending.job_id)
        assert persisted is not generating
        assert persisted is not None
        assert persisted.status is GenerationJobStatus.GENERATING

    asyncio.run(scenario())


def test_store_rejects_duplicate_job_and_stale_status() -> None:
    async def scenario() -> None:
        store = InMemoryJobStore()
        pending = _job()
        await store.create(pending)
        with pytest.raises(DuplicateJobError):
            await store.create(pending)
        generating = GenerationJobStateMachine.transition(
            pending, GenerationJobStatus.GENERATING
        )
        await store.replace(
            generating, expected_status=GenerationJobStatus.PENDING
        )
        with pytest.raises(JobConcurrencyError, match="changed concurrently"):
            await store.replace(
                generating, expected_status=GenerationJobStatus.PENDING
            )

    asyncio.run(scenario())


def test_store_claims_one_job_for_concurrent_idempotency_key() -> None:
    async def scenario() -> None:
        store = InMemoryJobStore()
        first = _job()
        second = first.model_copy(update={"job_id": "job-002"})

        claims = await asyncio.gather(
            store.create_or_get(first, idempotency_key="delivery-1"),
            store.create_or_get(second, idempotency_key="delivery-1"),
        )

        assert sum(claim.created for claim in claims) == 1
        assert {claim.job.job_id for claim in claims} == {"job-001"}
        with pytest.raises(ValueError, match="must not be empty"):
            await store.create_or_get(second, idempotency_key=" ")

    asyncio.run(scenario())


def test_store_lease_takeover_heartbeat_and_fencing() -> None:
    async def scenario() -> None:
        store = InMemoryJobStore()
        await store.create(_job())
        started_at = datetime.now(UTC)
        first = await store.claim_next(
            worker_id="worker-1",
            lease_duration=timedelta(seconds=10),
            now=started_at,
        )
        assert first is not None
        assert (
            await store.claim_next(
                worker_id="worker-2",
                lease_duration=timedelta(seconds=10),
                now=started_at + timedelta(seconds=5),
            )
            is None
        )
        renewed = await store.renew_lease(
            job_id=first.job.job_id,
            lease_token=first.token,
            lease_duration=timedelta(seconds=10),
            now=started_at + timedelta(seconds=5),
        )
        assert renewed.expires_at == started_at + timedelta(seconds=15)

        takeover = await store.claim_next(
            worker_id="worker-2",
            lease_duration=timedelta(seconds=30),
            now=started_at + timedelta(seconds=16),
        )
        assert takeover is not None
        assert takeover.token != first.token
        generating = GenerationJobStateMachine.transition(
            takeover.job, GenerationJobStatus.GENERATING
        )
        with pytest.raises(JobLeaseConflictError):
            await store.replace(
                generating,
                expected_status=GenerationJobStatus.PENDING,
                lease_token=first.token,
            )
        await store.replace(
            generating,
            expected_status=GenerationJobStatus.PENDING,
            lease_token=takeover.token,
        )

        recovered = await store.recover_abandoned(
            now=started_at + timedelta(seconds=47)
        )
        assert len(recovered) == 1
        assert recovered[0].status is GenerationJobStatus.FAILED
        assert recovered[0].error == "JobLeaseExpired"

    asyncio.run(scenario())


def test_store_rejects_invalid_or_replaced_lease() -> None:
    async def scenario() -> None:
        store = InMemoryJobStore()
        await store.create(_job())
        with pytest.raises(ValueError, match="worker_id"):
            await store.claim_next(
                worker_id=" ", lease_duration=timedelta(seconds=1)
            )
        lease = await store.claim_next(
            worker_id="worker-1", lease_duration=timedelta(seconds=30)
        )
        assert lease is not None
        with pytest.raises(JobLeaseConflictError):
            await store.renew_lease(
                job_id=lease.job.job_id,
                lease_token="wrong",
                lease_duration=timedelta(seconds=30),
            )
        with pytest.raises(JobLeaseConflictError):
            await store.release_lease(
                job_id=lease.job.job_id, lease_token="wrong"
            )
        await store.release_lease(
            job_id=lease.job.job_id, lease_token=lease.token
        )

    asyncio.run(scenario())
