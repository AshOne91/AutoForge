from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoforge.core.migration import (
    AppliedMigration,
    MigrationArtifact,
)
from autoforge.infrastructure.postgresql.control_plane import MigrationVersionRecord


class PostgreSQLMigrationVersionLedger:
    """PostgreSQL durable migration evidence with idempotent repeat records."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def list_applied(self) -> tuple[AppliedMigration, ...]:
        async with self._sessions() as session:
            return await self.list_applied_in_session(session)

    async def list_applied_in_session(
        self, session: AsyncSession
    ) -> tuple[AppliedMigration, ...]:
        statement = select(MigrationVersionRecord).order_by(MigrationVersionRecord.version)
        records = (await session.execute(statement)).scalars().all()
        return tuple(_to_applied(record) for record in records)

    async def record_applied(
        self, artifact: MigrationArtifact
    ) -> AppliedMigration:
        async with self._sessions() as session, session.begin():
            return await self.record_applied_in_session(session, artifact)

    async def record_applied_in_session(
        self,
        session: AsyncSession,
        artifact: MigrationArtifact,
    ) -> AppliedMigration:
        statement = (
            insert(MigrationVersionRecord)
            .values(
                version=artifact.version,
                path=artifact.path.as_posix(),
                checksum=artifact.checksum,
            )
            .on_conflict_do_nothing(index_elements=("version",))
            .returning(MigrationVersionRecord)
        )
        record = (await session.execute(statement)).scalar_one_or_none()
        if record is None:
            record = await session.get(MigrationVersionRecord, artifact.version)
            if record is None:
                raise RuntimeError("PostgreSQL did not return the migration record")
            if (
                record.path != artifact.path.as_posix()
                or record.checksum != artifact.checksum
            ):
                raise ValueError(
                    "migration version is already recorded with a different artifact"
                )
        return _to_applied(record)


def _to_applied(record: MigrationVersionRecord) -> AppliedMigration:
    if record.applied_at is None:
        raise RuntimeError("PostgreSQL returned an incomplete migration record")
    return AppliedMigration(
        version=record.version,
        path=record.path,
        checksum=record.checksum,
        applied_at=record.applied_at,
    )
