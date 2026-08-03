import asyncio
import os
from datetime import UTC, datetime

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from autoforge.core.audit import AuditRecord
from autoforge.core.generation import content_hash
from autoforge.core.job import (
    GenerationJob,
    GenerationJobStateMachine,
    GenerationJobStatus,
    GenerationUnit,
    GenerationUnitKind,
    JobConcurrencyError,
)
from autoforge.infrastructure.audit.postgresql import PostgreSQLAuditSink
from autoforge.infrastructure.job.postgresql import PostgreSQLJobStore
from autoforge.infrastructure.postgresql.control_plane import AuditRecordRow

DATABASE_URL = os.getenv("AUTOFORGE_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        DATABASE_URL is None,
        reason="AUTOFORGE_TEST_DATABASE_URL is required",
    ),
]


def _job(job_id: str) -> GenerationJob:
    return GenerationJob(
        job_id=job_id,
        units=[
            GenerationUnit(
                unit_id="project",
                kind=GenerationUnitKind.PROJECT,
                specification_version="1",
                specification_hash=content_hash("project"),
            )
        ],
    )


def test_postgresql_job_claim_cas_and_audit_idempotency() -> None:
    async def scenario() -> None:
        assert DATABASE_URL is not None
        engine = create_async_engine(DATABASE_URL)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        first_store = PostgreSQLJobStore(sessions)
        second_store = PostgreSQLJobStore(sessions)
        audit = PostgreSQLAuditSink(sessions)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "TRUNCATE autoforge_audit_records, "
                        "autoforge_generation_jobs"
                    )
                )

            claims = await asyncio.gather(
                first_store.create_or_get(
                    _job("job-001"), idempotency_key="github-delivery-1"
                ),
                second_store.create_or_get(
                    _job("job-002"), idempotency_key="github-delivery-1"
                ),
            )

            assert sum(claim.created for claim in claims) == 1
            claimed_ids = {claim.job.job_id for claim in claims}
            assert len(claimed_ids) == 1
            claimed_id = claimed_ids.pop()
            pending = await first_store.get(claimed_id)
            assert pending is not None
            generating = GenerationJobStateMachine.transition(
                pending, GenerationJobStatus.GENERATING
            )
            results = await asyncio.gather(
                first_store.replace(
                    generating, expected_status=GenerationJobStatus.PENDING
                ),
                second_store.replace(
                    generating, expected_status=GenerationJobStatus.PENDING
                ),
                return_exceptions=True,
            )
            assert sum(result is None for result in results) == 1
            assert sum(isinstance(result, JobConcurrencyError) for result in results) == 1

            record = AuditRecord(
                event_id="event-001",
                event_type="GenerationStartedEvent",
                event_version="1",
                event_created_at=datetime.now(UTC),
                correlation_id=claimed_id,
                causation_id=None,
                job_id=claimed_id,
                producer="integration_test",
            )
            await asyncio.gather(audit.append(record), audit.append(record))
            async with sessions() as session:
                audit_count = await session.scalar(
                    select(func.count()).select_from(AuditRecordRow)
                )
            assert audit_count == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())
