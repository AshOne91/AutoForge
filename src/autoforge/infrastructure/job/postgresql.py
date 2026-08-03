from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoforge.core.job.models import GenerationJob, GenerationJobStatus
from autoforge.core.job.state import GenerationJobStateMachine
from autoforge.core.job.store import (
    DuplicateJobError,
    JobClaim,
    JobConcurrencyError,
    JobLease,
    JobLeaseConflictError,
)
from autoforge.infrastructure.postgresql.control_plane import GenerationJobRecord


class PostgreSQLJobStore:
    """PostgreSQL JobStore with status CAS and idempotent job claiming."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create(self, job: GenerationJob) -> None:
        async with self._sessions() as session:
            session.add(self._record(job))
            try:
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                raise DuplicateJobError(
                    f"GenerationJob already exists: {job.job_id}"
                ) from error

    async def create_or_get(
        self, job: GenerationJob, *, idempotency_key: str
    ) -> JobClaim:
        if not idempotency_key.strip():
            raise ValueError("idempotency_key must not be empty")
        values = self._values(job)
        values["idempotency_key"] = idempotency_key
        statement = (
            insert(GenerationJobRecord)
            .values(**values)
            .on_conflict_do_nothing()
            .returning(GenerationJobRecord.job_id)
        )
        async with self._sessions() as session, session.begin():
            created_id = (await session.execute(statement)).scalar_one_or_none()
            if created_id is not None:
                return JobClaim(job.model_copy(deep=True), True)
            existing = (
                await session.execute(
                    select(GenerationJobRecord).where(
                        GenerationJobRecord.idempotency_key == idempotency_key
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                raise DuplicateJobError(
                    f"GenerationJob already exists: {job.job_id}"
                )
            return JobClaim(self._to_job(existing), False)

    async def get(self, job_id: str) -> GenerationJob | None:
        async with self._sessions() as session:
            record = await session.get(GenerationJobRecord, job_id)
            return None if record is None else self._to_job(record)

    async def claim_next(
        self,
        *,
        worker_id: str,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> JobLease | None:
        _validate_lease_request(worker_id, lease_duration)
        async with self._sessions() as session, session.begin():
            current_time = await _current_time(session, now)
            token = str(uuid4())
            candidate = (
                select(GenerationJobRecord.job_id)
                .where(
                    GenerationJobRecord.status
                    == GenerationJobStatus.PENDING.value,
                    or_(
                        GenerationJobRecord.lease_token.is_(None),
                        GenerationJobRecord.lease_expires_at <= current_time,
                    ),
                )
                .order_by(
                    GenerationJobRecord.created_at,
                    GenerationJobRecord.job_id,
                )
                .limit(1)
                .with_for_update(skip_locked=True)
                .cte()
            )
            statement = (
                update(GenerationJobRecord)
                .where(GenerationJobRecord.job_id == candidate.c.job_id)
                .values(
                    lease_owner=worker_id,
                    lease_token=token,
                    lease_expires_at=current_time + lease_duration,
                    heartbeat_at=current_time,
                    revision=GenerationJobRecord.revision + 1,
                )
                .returning(GenerationJobRecord)
            )
            record = (await session.execute(statement)).scalar_one_or_none()
            if record is None:
                return None
            return self._lease(record)

    async def renew_lease(
        self,
        *,
        job_id: str,
        lease_token: str,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> JobLease:
        _validate_lease_request("worker", lease_duration)
        async with self._sessions() as session, session.begin():
            current_time = await _current_time(session, now)
            statement = (
                update(GenerationJobRecord)
                .where(
                    GenerationJobRecord.job_id == job_id,
                    GenerationJobRecord.lease_token == lease_token,
                    GenerationJobRecord.lease_expires_at > current_time,
                    GenerationJobRecord.status.not_in(
                        (
                            GenerationJobStatus.SUCCEEDED.value,
                            GenerationJobStatus.FAILED.value,
                        )
                    ),
                )
                .values(
                    lease_expires_at=current_time + lease_duration,
                    heartbeat_at=current_time,
                    revision=GenerationJobRecord.revision + 1,
                )
                .returning(GenerationJobRecord)
            )
            record = (await session.execute(statement)).scalar_one_or_none()
            if record is None:
                raise JobLeaseConflictError(
                    f"GenerationJob lease is missing, expired, or replaced: {job_id}"
                )
            return self._lease(record)

    async def release_lease(self, *, job_id: str, lease_token: str) -> None:
        statement = (
            update(GenerationJobRecord)
            .where(
                GenerationJobRecord.job_id == job_id,
                GenerationJobRecord.lease_token == lease_token,
            )
            .values(
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
                heartbeat_at=None,
                revision=GenerationJobRecord.revision + 1,
            )
        )
        async with self._sessions() as session, session.begin():
            result = await session.execute(statement)
            if result.rowcount != 1:
                raise JobLeaseConflictError(
                    f"GenerationJob lease is missing or replaced: {job_id}"
                )

    async def recover_abandoned(
        self, *, now: datetime | None = None
    ) -> tuple[GenerationJob, ...]:
        async with self._sessions() as session, session.begin():
            current_time = await _current_time(session, now)
            records = (
                await session.execute(
                    select(GenerationJobRecord)
                    .where(
                        GenerationJobRecord.status.in_(
                            (
                                GenerationJobStatus.GENERATING.value,
                                GenerationJobStatus.VALIDATING.value,
                                GenerationJobStatus.COMMITTING.value,
                            )
                        ),
                        GenerationJobRecord.lease_expires_at <= current_time,
                    )
                    .order_by(GenerationJobRecord.job_id)
                    .with_for_update(skip_locked=True)
                )
            ).scalars()
            recovered: list[GenerationJob] = []
            for record in records:
                failed = GenerationJobStateMachine.transition(
                    self._to_job(record),
                    GenerationJobStatus.FAILED,
                    error="JobLeaseExpired",
                )
                record.status = failed.status.value
                record.document = failed.model_dump(mode="json")
                record.revision += 1
                record.lease_owner = None
                record.lease_token = None
                record.lease_expires_at = None
                record.heartbeat_at = None
                recovered.append(failed)
            return tuple(recovered)

    async def replace(
        self,
        job: GenerationJob,
        *,
        expected_status: GenerationJobStatus,
        lease_token: str | None = None,
    ) -> None:
        async with self._sessions() as session, session.begin():
            current_time = await _current_time(session, None)
            lease_condition = (
                GenerationJobRecord.lease_token.is_(None)
                if lease_token is None
                else (
                    (GenerationJobRecord.lease_token == lease_token)
                    & (GenerationJobRecord.lease_expires_at > current_time)
                )
            )
            values: dict[str, object] = {
                "status": job.status.value,
                "document": job.model_dump(mode="json"),
                "revision": GenerationJobRecord.revision + 1,
            }
            if job.status in {
                GenerationJobStatus.SUCCEEDED,
                GenerationJobStatus.FAILED,
            }:
                values.update(
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                    heartbeat_at=None,
                )
            statement = (
                update(GenerationJobRecord)
                .where(
                    GenerationJobRecord.job_id == job.job_id,
                    GenerationJobRecord.status == expected_status.value,
                    lease_condition,
                )
                .values(**values)
            )
            result = await session.execute(statement)
            if result.rowcount != 1:
                error_type = (
                    JobConcurrencyError
                    if lease_token is None
                    else JobLeaseConflictError
                )
                raise error_type(
                    "GenerationJob status changed concurrently or does not exist: "
                    f"job_id={job.job_id}, expected={expected_status.value}"
                )

    @staticmethod
    def _record(job: GenerationJob) -> GenerationJobRecord:
        return GenerationJobRecord(**PostgreSQLJobStore._values(job))

    @staticmethod
    def _values(job: GenerationJob) -> dict[str, object]:
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "document": job.model_dump(mode="json"),
            "revision": 0,
        }

    @staticmethod
    def _to_job(record: GenerationJobRecord) -> GenerationJob:
        return GenerationJob.model_validate(record.document)

    @staticmethod
    def _lease(record: GenerationJobRecord) -> JobLease:
        if (
            record.lease_owner is None
            or record.lease_token is None
            or record.lease_expires_at is None
        ):
            raise RuntimeError("PostgreSQL returned an incomplete Job lease")
        return JobLease(
            job=PostgreSQLJobStore._to_job(record),
            worker_id=record.lease_owner,
            token=record.lease_token,
            expires_at=record.lease_expires_at,
        )


async def _current_time(
    session: AsyncSession, value: datetime | None
) -> datetime:
    if value is not None:
        if value.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        return value
    result = await session.scalar(select(func.now()))
    if result is None:
        raise RuntimeError("PostgreSQL did not return its current time")
    return result


def _validate_lease_request(worker_id: str, duration: timedelta) -> None:
    if not worker_id.strip():
        raise ValueError("worker_id must not be empty")
    if duration <= timedelta(0):
        raise ValueError("lease_duration must be positive")
