from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoforge.core.job.models import GenerationJob, GenerationJobStatus
from autoforge.core.job.store import (
    DuplicateJobError,
    JobClaim,
    JobConcurrencyError,
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

    async def replace(
        self,
        job: GenerationJob,
        *,
        expected_status: GenerationJobStatus,
    ) -> None:
        statement = (
            update(GenerationJobRecord)
            .where(
                GenerationJobRecord.job_id == job.job_id,
                GenerationJobRecord.status == expected_status.value,
            )
            .values(
                status=job.status.value,
                document=job.model_dump(mode="json"),
                revision=GenerationJobRecord.revision + 1,
            )
        )
        async with self._sessions() as session, session.begin():
            result = await session.execute(statement)
            if result.rowcount != 1:
                raise JobConcurrencyError(
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
