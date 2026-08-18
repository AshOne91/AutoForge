import asyncio
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath

import httpx
import pytest

pytest.importorskip("sqlalchemy")
asyncpg = pytest.importorskip("asyncpg")

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from autoforge.application.generation import (
    GenerationJobPipeline,
    GenerationSubmissionService,
    GenerationTriggerRequest,
    GenerationWorker,
    GenerationWorkerLoop,
    GenerationWorkerLoopSettings,
    GenerationWorkerSettings,
)
from autoforge.core.audit import AuditRecord
from autoforge.core.event import EventBus
from autoforge.core.generation import content_hash
from autoforge.core.git import (
    GitCheckoutRequest,
    GitCommitResult,
    GitPullRequestResult,
    GitPushResult,
)
from autoforge.core.job import (
    GenerationJob,
    GenerationJobStateMachine,
    GenerationJobStatus,
    GenerationJobSubmission,
    GenerationUnit,
    GenerationUnitKind,
    JobConcurrencyError,
    JobLeaseConflictError,
)
from autoforge.core.migration import MigrationArtifact
from autoforge.infrastructure.audit.postgresql import PostgreSQLAuditSink
from autoforge.infrastructure.http import (
    ControlPlaneHTTPSettings,
    create_control_plane_app,
)
from autoforge.infrastructure.job.postgresql import PostgreSQLJobStore
from autoforge.infrastructure.migration import (
    PostgreSQLMigrationExecutor,
    PostgreSQLMigrationVersionLedger,
)
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
from tests.core.test_generation_job import job_manifest

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


class SlowValidator:
    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def validate(self, **_: object) -> ProjectValidationResult:
        self.started.set()
        await asyncio.sleep(60)
        raise AssertionError("validator should be cancelled")


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


def test_postgresql_persists_migration_version_ledger() -> None:
    async def scenario() -> None:
        assert DATABASE_URL is not None
        engine = create_async_engine(DATABASE_URL)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        ledger = PostgreSQLMigrationVersionLedger(sessions)
        artifact = MigrationArtifact(
            version=900001,
            path="deploy/postgresql/init/900001_ledger_test.sql",
            sql="SELECT 1;",
        )
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "DELETE FROM autoforge_migration_versions "
                        "WHERE version = :version"
                    ),
                    {"version": artifact.version},
                )
            first = await ledger.record_applied(artifact)
            repeated = await ledger.record_applied(artifact)
            applied = await ledger.list_applied()

            assert first == repeated
            assert [record.version for record in applied if record.version == artifact.version] == [
                artifact.version
            ]
            with pytest.raises(ValueError, match="different artifact"):
                await ledger.record_applied(
                    MigrationArtifact(
                        version=artifact.version,
                        path=artifact.path,
                        sql="SELECT 2;",
                    )
                )
        finally:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "DELETE FROM autoforge_migration_versions "
                        "WHERE version = :version"
                    ),
                    {"version": artifact.version},
                )
            await engine.dispose()

    asyncio.run(scenario())


def test_postgresql_migration_executor_applies_once_and_rolls_back() -> None:
    async def scenario() -> None:
        assert DATABASE_URL is not None
        engine = create_async_engine(DATABASE_URL)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        executor = PostgreSQLMigrationExecutor(sessions)
        ledger = PostgreSQLMigrationVersionLedger(sessions)
        successful = MigrationArtifact(
            version=900010,
            path="900010_executor_probe.sql",
            sql=(
                "CREATE TABLE autoforge_migration_executor_probe (value INTEGER NOT NULL);\n"
                "INSERT INTO autoforge_migration_executor_probe (value) VALUES (1);"
            ),
        )
        rolled_back = MigrationArtifact(
            version=900011,
            path="900011_executor_rollback_probe.sql",
            sql="CREATE TABLE autoforge_migration_executor_rollback_probe (value INTEGER);",
        )
        failed = MigrationArtifact(
            version=900012,
            path="900012_executor_failure.sql",
            sql="SELECT not_valid_postgresql_syntax;",
        )
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text("DROP TABLE IF EXISTS autoforge_migration_executor_probe")
                )
                await connection.execute(
                    text("DROP TABLE IF EXISTS autoforge_migration_executor_rollback_probe")
                )
                await connection.execute(
                    text(
                        "DELETE FROM autoforge_migration_versions "
                        "WHERE version IN (:successful, :rolled_back, :failed)"
                    ).bindparams(
                        successful=successful.version,
                        rolled_back=rolled_back.version,
                        failed=failed.version,
                    )
                )

            concurrent_results = await asyncio.gather(
                executor.apply((successful,)),
                executor.apply((successful,)),
            )
            async with engine.connect() as connection:
                value = await connection.scalar(
                    text("SELECT value FROM autoforge_migration_executor_probe")
                )
            with pytest.raises(asyncpg.PostgresError):
                await executor.apply((rolled_back, failed))
            async with engine.connect() as connection:
                rolled_back_table = await connection.scalar(
                    text(
                        "SELECT to_regclass("
                        "'autoforge_migration_executor_rollback_probe')"
                    )
                )
            applied_versions = {
                record.version for record in await ledger.list_applied()
            }

            assert sorted(len(result) for result in concurrent_results) == [0, 1]
            assert [
                record.version
                for result in concurrent_results
                for record in result
            ] == [successful.version]
            assert value == 1
            assert successful.version in applied_versions
            assert rolled_back_table is None
            assert rolled_back.version not in applied_versions
            assert failed.version not in applied_versions
        finally:
            async with engine.begin() as connection:
                await connection.execute(
                    text("DROP TABLE IF EXISTS autoforge_migration_executor_probe")
                )
                await connection.execute(
                    text("DROP TABLE IF EXISTS autoforge_migration_executor_rollback_probe")
                )
                await connection.execute(
                    text(
                        "DELETE FROM autoforge_migration_versions "
                        "WHERE version IN (900010, 900011, 900012)"
                    )
                )
            await engine.dispose()

    asyncio.run(scenario())


def test_postgresql_migration_executor_bootstraps_missing_ledger() -> None:
    async def scenario() -> None:
        assert DATABASE_URL is not None
        schema = "autoforge_migration_executor_bootstrap"
        admin_engine = create_async_engine(DATABASE_URL)
        engine = create_async_engine(
            DATABASE_URL,
            connect_args={"server_settings": {"search_path": schema}},
        )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        executor = PostgreSQLMigrationExecutor(sessions)
        ledger = PostgreSQLMigrationVersionLedger(sessions)
        artifacts = (
            MigrationArtifact(
                version=1,
                path="001_bootstrap_probe.sql",
                sql="CREATE TABLE bootstrap_probe (value INTEGER NOT NULL);",
            ),
            MigrationArtifact(
                version=2,
                path="002_migration_versions.sql",
                sql=(
                    "CREATE TABLE autoforge_migration_versions ("
                    "version INTEGER PRIMARY KEY, path VARCHAR(512) NOT NULL, "
                    "checksum CHAR(64) NOT NULL, "
                    "applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW());"
                ),
            ),
        )
        try:
            async with admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
                await connection.execute(text(f"CREATE SCHEMA {schema}"))

            applied = await executor.apply(artifacts)
            persisted = await ledger.list_applied()
            async with engine.connect() as connection:
                probe_exists = await connection.scalar(
                    text("SELECT to_regclass('bootstrap_probe')")
                )

            assert [record.version for record in applied] == [1, 2]
            assert [record.version for record in persisted] == [1, 2]
            assert probe_exists == "bootstrap_probe"
        finally:
            await engine.dispose()
            async with admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
            await admin_engine.dispose()

    asyncio.run(scenario())


def test_control_plane_migration_cli_runs_in_subprocess(tmp_path: Path) -> None:
    async def cleanup() -> None:
        assert DATABASE_URL is not None
        engine = create_async_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text("DROP TABLE IF EXISTS autoforge_migration_cli_probe")
                )
                await connection.execute(
                    text(
                        "DELETE FROM autoforge_migration_versions WHERE version = 900020"
                    )
                )
        finally:
            await engine.dispose()

    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "900020_cli_probe.sql").write_text(
        "CREATE TABLE autoforge_migration_cli_probe (value INTEGER NOT NULL);",
        encoding="utf-8",
    )
    environment = {**os.environ, "AUTOFORGE_DATABASE_URL": DATABASE_URL or ""}
    command = [
        sys.executable,
        "-m",
        "autoforge.main",
        "migrate-control-plane",
        "--migration-directory",
        str(migrations),
    ]
    try:
        asyncio.run(cleanup())
        first = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            env=environment,
        )
        second = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            env=environment,
        )

        assert first.returncode == 0, first.stderr
        assert first.stdout == "900020\n"
        assert second.returncode == 0, second.stderr
        assert second.stdout == ""
        assert first.stderr == ""
    finally:
        asyncio.run(cleanup())


def test_control_plane_migration_cli_contains_failed_batch(tmp_path: Path) -> None:
    async def cleanup() -> None:
        assert DATABASE_URL is not None
        engine = create_async_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text("DROP TABLE IF EXISTS autoforge_migration_cli_failure_probe")
                )
                await connection.execute(
                    text(
                        "DELETE FROM autoforge_migration_versions "
                        "WHERE version IN (900021, 900022)"
                    )
                )
        finally:
            await engine.dispose()

    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "900021_failure_probe.sql").write_text(
        "CREATE TABLE autoforge_migration_cli_failure_probe (value INTEGER NOT NULL);",
        encoding="utf-8",
    )
    (migrations / "900022_failure.sql").write_text(
        "SELECT not_valid_postgresql_syntax;",
        encoding="utf-8",
    )
    environment = {**os.environ, "AUTOFORGE_DATABASE_URL": DATABASE_URL or ""}
    command = [
        sys.executable,
        "-m",
        "autoforge.main",
        "migrate-control-plane",
        "--migration-directory",
        str(migrations),
    ]
    try:
        asyncio.run(cleanup())
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            env=environment,
        )
        assert result.returncode == 1
        assert result.stdout == ""
        assert "Error: Control Plane migration failed:" in result.stderr
        assert "validation" not in result.stderr
        assert "not_valid_postgresql_syntax" not in result.stderr

        async def verify() -> tuple[object | None, int]:
            assert DATABASE_URL is not None
            engine = create_async_engine(DATABASE_URL)
            try:
                async with engine.connect() as connection:
                    table = await connection.scalar(
                        text("SELECT to_regclass('autoforge_migration_cli_failure_probe')")
                    )
                    count = await connection.scalar(
                        text(
                            "SELECT count(*) FROM autoforge_migration_versions "
                            "WHERE version IN (900021, 900022)"
                        )
                    )
                    assert count is not None
                    return table, count
            finally:
                await engine.dispose()

        table, count = asyncio.run(verify())
        assert table is None
        assert count == 0
    finally:
        asyncio.run(cleanup())


def test_postgresql_persists_committing_lifecycle_and_commit_result() -> None:
    async def scenario() -> None:
        assert DATABASE_URL is not None
        engine = create_async_engine(DATABASE_URL)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        store = PostgreSQLJobStore(sessions)
        manifest = job_manifest("job-commit")
        job = GenerationJob(
            job_id="job-commit",
            units=[
                GenerationUnit(
                    unit_id=unit.unit_id,
                    kind=unit.kind,
                    specification_version=unit.manifest.specification_version,
                    specification_hash=unit.manifest.specification_hash,
                )
                for unit in manifest.units
            ],
            submission=GenerationJobSubmission(
                project_path="spec/project.yaml",
                specifications_path="spec/modules",
                output_path=".",
                repository=GitCheckoutRequest(
                    "https://github.com/example/repository.git", "main"
                ),
                resolved_commit_sha="a" * 40,
            ),
        )
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text("TRUNCATE autoforge_generation_jobs")
                )
            await store.create(job)
            lease = await store.claim_next(
                worker_id="worker-commit",
                lease_duration=timedelta(seconds=30),
            )
            assert lease is not None
            generating = GenerationJobStateMachine.transition(
                lease.job, GenerationJobStatus.GENERATING
            )
            await store.replace(
                generating,
                expected_status=GenerationJobStatus.PENDING,
                lease_token=lease.token,
            )
            validating = GenerationJobStateMachine.transition(
                generating,
                GenerationJobStatus.VALIDATING,
                manifest=manifest,
            )
            await store.replace(
                validating,
                expected_status=GenerationJobStatus.GENERATING,
                lease_token=lease.token,
            )
            committing = GenerationJobStateMachine.transition(
                validating, GenerationJobStatus.COMMITTING
            )
            await store.replace(
                committing,
                expected_status=GenerationJobStatus.VALIDATING,
                lease_token=lease.token,
            )
            pushing = GenerationJobStateMachine.transition(
                committing,
                GenerationJobStatus.PUSHING,
                git_commit=GitCommitResult(
                    commit_sha="b" * 40,
                    branch_name="autoforge/job-commit",
                    changed_paths=(PurePosixPath("src/service.py"),),
                    commit_created=True,
                ),
            )
            await store.replace(
                pushing,
                expected_status=GenerationJobStatus.COMMITTING,
                lease_token=lease.token,
            )
            opening_pull_request = GenerationJobStateMachine.transition(
                pushing,
                GenerationJobStatus.OPENING_PULL_REQUEST,
                git_push=GitPushResult(
                    commit_sha="b" * 40,
                    branch_name="autoforge/job-commit",
                    remote_url="https://github.com/example/repository.git",
                    pushed=True,
                ),
            )
            await store.replace(
                opening_pull_request,
                expected_status=GenerationJobStatus.PUSHING,
                lease_token=lease.token,
            )
            succeeded = GenerationJobStateMachine.transition(
                opening_pull_request,
                GenerationJobStatus.SUCCEEDED,
                git_pull_request=GitPullRequestResult(
                    pull_request_id="42",
                    url="https://github.com/example/repository/pull/42",
                    head_sha="b" * 40,
                    head_branch="autoforge/job-commit",
                    base_branch="main",
                    created=True,
                ),
            )
            await store.replace(
                succeeded,
                expected_status=GenerationJobStatus.OPENING_PULL_REQUEST,
                lease_token=lease.token,
            )

            persisted = await store.get(job.job_id)
            assert persisted == succeeded
            assert persisted is not None
            assert persisted.git_commit is not None
            assert persisted.git_commit.commit_sha == "b" * 40
            assert persisted.git_push is not None
            assert persisted.git_push.pushed is True
            assert persisted.git_pull_request is not None
            assert persisted.git_pull_request.pull_request_id == "42"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


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


def test_worker_shutdown_timeout_is_recovered_after_lease_expiry(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        assert DATABASE_URL is not None
        _write_specifications(tmp_path)
        output_root = tmp_path / "shutdown-output"
        output_root.mkdir()
        engine = create_async_engine(DATABASE_URL)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        store = PostgreSQLJobStore(sessions)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text("TRUNCATE autoforge_generation_jobs")
                )
            submitted = await GenerationSubmissionService(
                source_root=tmp_path,
                output_root=output_root,
                job_store=store,
                event_bus=EventBus(),
            ).trigger(
                GenerationTriggerRequest(
                    project_path="spec/project.yaml",
                    specifications_path="spec/modules",
                    output_path="generated/service",
                ),
                idempotency_key="shutdown-delivery-1",
            )
            validator = SlowValidator()
            bus = EventBus()
            worker = GenerationWorker(
                settings=GenerationWorkerSettings(
                    worker_id="worker-shutdown",
                    source_root=tmp_path,
                    output_root=output_root,
                    lease_duration=timedelta(seconds=2),
                    heartbeat_interval=timedelta(milliseconds=100),
                ),
                job_store=store,
                pipeline=GenerationJobPipeline(
                    job_store=store,
                    event_bus=bus,
                    validator=validator,
                ),
            )
            loop = GenerationWorkerLoop(
                worker=worker,
                job_store=store,
                settings=GenerationWorkerLoopSettings(
                    idle_poll_interval=timedelta(milliseconds=10),
                    error_backoff=timedelta(milliseconds=10),
                    abandoned_sweep_interval=timedelta(seconds=1),
                    shutdown_grace_period=timedelta(milliseconds=10),
                ),
            )
            stop = asyncio.Event()
            loop_task = asyncio.create_task(loop.run(stop))
            await asyncio.wait_for(validator.started.wait(), timeout=5)
            stop.set()
            loop_result = await asyncio.wait_for(loop_task, timeout=5)

            assert loop_result.shutdown_timed_out is True
            interrupted = await store.get(submitted.job.job_id)
            assert interrupted is not None
            assert interrupted.status is GenerationJobStatus.VALIDATING

            recovered = await store.recover_abandoned(
                now=datetime.now(UTC) + timedelta(seconds=10)
            )
            assert len(recovered) == 1
            assert recovered[0].status is GenerationJobStatus.FAILED
            assert recovered[0].error == "JobLeaseExpired"
        finally:
            await engine.dispose()

    asyncio.run(scenario())
