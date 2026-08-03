import asyncio

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
