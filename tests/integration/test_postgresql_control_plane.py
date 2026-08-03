import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from autoforge.application.generation import (
    GenerationJobPipeline,
    GenerationSubmissionService,
    GenerationTriggerRequest,
    GenerationWorker,
    GenerationWorkerSettings,
)
from autoforge.core.audit import AuditRecord
from autoforge.core.event import EventBus
from autoforge.core.generation import content_hash
from autoforge.core.job import (
    GenerationJob,
    GenerationJobStateMachine,
    GenerationJobStatus,
    GenerationUnit,
    GenerationUnitKind,
    JobConcurrencyError,
    JobLeaseConflictError,
)
from autoforge.infrastructure.audit.postgresql import PostgreSQLAuditSink
from autoforge.infrastructure.http import (
    ControlPlaneHTTPSettings,
    create_control_plane_app,
)
from autoforge.infrastructure.job.postgresql import PostgreSQLJobStore
from autoforge.infrastructure.postgresql.control_plane import (
    AuditRecordRow,
    GenerationJobRecord,
)
from autoforge.services.validation import (
    ProcessResult,
    ProjectValidationResult,
    ValidationStep,
    ValidationStepResult,
)

DATABASE_URL = os.getenv("AUTOFORGE_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        DATABASE_URL is None,
        reason="AUTOFORGE_TEST_DATABASE_URL is required",
    ),
]


class SuccessfulValidator:
    async def validate(self, **_: object) -> ProjectValidationResult:
        return ProjectValidationResult(
            steps=(
                ValidationStepResult(
                    step=ValidationStep.IMPORT,
                    process=ProcessResult(
                        command=("python",),
                        exit_code=0,
                        stdout="",
                        stderr="",
                        timed_out=False,
                        duration_seconds=0,
                    ),
                ),
            )
        )


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


def _write_specifications(root: Path) -> None:
    modules = root / "spec" / "modules"
    modules.mkdir(parents=True)
    (root / "spec" / "project.yaml").write_text(
        """spec_version: "1"
project:
  name: Sample
  package_name: sample
  version: "0.1.0"
application:
  modules:
    - account
""",
        encoding="utf-8",
    )
    (modules / "account.yaml").write_text(
        """spec_version: "1"
module:
  name: account
  display_name: Account
  route_prefix: /account
""",
        encoding="utf-8",
    )


def test_two_control_plane_apps_claim_one_postgresql_job(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        assert DATABASE_URL is not None
        _write_specifications(tmp_path)
        output_root = tmp_path / "output"
        output_root.mkdir()
        engine = create_async_engine(DATABASE_URL)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text("TRUNCATE autoforge_generation_jobs")
                )
            apps = [
                create_control_plane_app(
                    service=GenerationSubmissionService(
                        source_root=tmp_path,
                        output_root=output_root,
                        job_store=PostgreSQLJobStore(sessions),
                        event_bus=EventBus(),
                    ),
                    settings=ControlPlaneHTTPSettings(api_token="integration-token"),
                )
                for _ in range(2)
            ]
            clients = [
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://test",
                )
                for app in apps
            ]
            payload = {
                "project_path": "spec/project.yaml",
                "specifications_path": "spec/modules",
                "output_path": "generated/service",
            }
            headers = {
                "Authorization": "Bearer integration-token",
                "Idempotency-Key": "github-delivery-api-1",
            }
            try:
                responses = await asyncio.gather(
                    *(
                        client.post(
                            "/v1/generation-jobs",
                            json=payload,
                            headers=headers,
                        )
                        for client in clients
                    )
                )
            finally:
                await asyncio.gather(*(client.aclose() for client in clients))

            assert sorted(response.status_code for response in responses) == [200, 202]
            assert len(
                {response.json()["job"]["job_id"] for response in responses}
            ) == 1
            async with sessions() as session:
                job_count = await session.scalar(
                    select(func.count()).select_from(GenerationJobRecord)
                )
            assert job_count == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_postgresql_lease_heartbeat_takeover_and_abandoned_recovery() -> None:
    async def scenario() -> None:
        assert DATABASE_URL is not None
        engine = create_async_engine(DATABASE_URL)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        first_store = PostgreSQLJobStore(sessions)
        second_store = PostgreSQLJobStore(sessions)
        started_at = datetime.now(UTC)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text("TRUNCATE autoforge_generation_jobs")
                )
            await first_store.create(_job("lease-job"))
            claims = await asyncio.gather(
                first_store.claim_next(
                    worker_id="worker-1",
                    lease_duration=timedelta(seconds=10),
                    now=started_at,
                ),
                second_store.claim_next(
                    worker_id="worker-2",
                    lease_duration=timedelta(seconds=10),
                    now=started_at,
                ),
            )
            leases = [claim for claim in claims if claim is not None]
            assert len(leases) == 1
            first = leases[0]
            renewed = await first_store.renew_lease(
                job_id=first.job.job_id,
                lease_token=first.token,
                lease_duration=timedelta(seconds=10),
                now=started_at + timedelta(seconds=5),
            )
            assert renewed.expires_at == started_at + timedelta(seconds=15)

            takeover = await second_store.claim_next(
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
                await first_store.replace(
                    generating,
                    expected_status=GenerationJobStatus.PENDING,
                    lease_token=first.token,
                )
            await second_store.replace(
                generating,
                expected_status=GenerationJobStatus.PENDING,
                lease_token=takeover.token,
            )

            recovered = await first_store.recover_abandoned(
                now=started_at + timedelta(seconds=47)
            )
            assert len(recovered) == 1
            assert recovered[0].status is GenerationJobStatus.FAILED
            assert recovered[0].error == "JobLeaseExpired"
            async with sessions() as session:
                row = await session.get(GenerationJobRecord, "lease-job")
                assert row is not None
                assert row.lease_token is None
                assert row.status == GenerationJobStatus.FAILED.value
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_two_postgresql_workers_execute_one_generation_job(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        assert DATABASE_URL is not None
        _write_specifications(tmp_path)
        output_root = tmp_path / "worker-output"
        output_root.mkdir()
        engine = create_async_engine(DATABASE_URL)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text("TRUNCATE autoforge_generation_jobs")
                )
            submission_store = PostgreSQLJobStore(sessions)
            submitted = await GenerationSubmissionService(
                source_root=tmp_path,
                output_root=output_root,
                job_store=submission_store,
                event_bus=EventBus(),
            ).trigger(
                GenerationTriggerRequest(
                    project_path="spec/project.yaml",
                    specifications_path="spec/modules",
                    output_path="generated/service",
                ),
                idempotency_key="worker-delivery-1",
            )

            def worker(worker_id: str) -> GenerationWorker:
                store = PostgreSQLJobStore(sessions)
                bus = EventBus()
                return GenerationWorker(
                    settings=GenerationWorkerSettings(
                        worker_id=worker_id,
                        source_root=tmp_path,
                        output_root=output_root,
                        lease_duration=timedelta(seconds=5),
                        heartbeat_interval=timedelta(seconds=1),
                    ),
                    job_store=store,
                    pipeline=GenerationJobPipeline(
                        job_store=store,
                        event_bus=bus,
                        validator=SuccessfulValidator(),
                    ),
                )

            results = await asyncio.gather(
                worker("worker-a").run_once(),
                worker("worker-b").run_once(),
            )
            assert sum(result is not None for result in results) == 1
            persisted = await submission_store.get(submitted.job.job_id)
            assert persisted is not None
            assert persisted.status is GenerationJobStatus.SUCCEEDED
            assert (
                output_root / "generated/service/src/sample/main.py"
            ).is_file()
            async with sessions() as session:
                row = await session.get(
                    GenerationJobRecord, submitted.job.job_id
                )
                assert row is not None
                assert row.lease_token is None
        finally:
            await engine.dispose()

    asyncio.run(scenario())
