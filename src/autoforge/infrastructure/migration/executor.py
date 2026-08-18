from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoforge.core.migration import (
    AppliedMigration,
    MigrationArtifact,
    order_migrations,
)
from autoforge.infrastructure.migration.postgresql import (
    PostgreSQLMigrationVersionLedger,
)

_LOCK_STATEMENT = text(
    "SELECT pg_advisory_xact_lock(hashtext('autoforge_control_plane_migrations'))"
)
_LEDGER_EXISTS_STATEMENT = text(
    "SELECT to_regclass('autoforge_migration_versions') IS NOT NULL"
)


class PostgreSQLMigrationExecutor:
    """Provider-invoked executor for ordered Control Plane SQL artifacts."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions
        self._ledger = PostgreSQLMigrationVersionLedger(sessions)

    async def apply(
        self,
        artifacts: list[MigrationArtifact] | tuple[MigrationArtifact, ...],
    ) -> tuple[AppliedMigration, ...]:
        ordered = order_migrations(artifacts)
        async with self._sessions() as session, session.begin():
            await session.execute(_LOCK_STATEMENT)
            ledger_exists = await _ledger_exists(session)
            applied_by_version = (
                {record.version: record for record in await self._ledger.list_applied_in_session(session)}
                if ledger_exists
                else {}
            )
            newly_applied: list[AppliedMigration] = []
            pending_records: list[MigrationArtifact] = []
            for artifact in ordered:
                existing = applied_by_version.get(artifact.version)
                if existing is not None:
                    _validate_existing(existing, artifact)
                    continue
                await _execute_sql(session, artifact.sql)
                if await _ledger_exists(session):
                    for pending in pending_records:
                        newly_applied.append(
                            await self._ledger.record_applied_in_session(session, pending)
                        )
                    pending_records.clear()
                    newly_applied.append(
                        await self._ledger.record_applied_in_session(session, artifact)
                    )
                else:
                    pending_records.append(artifact)
            if pending_records:
                raise RuntimeError(
                    "migration ledger table was not created by the supplied artifacts"
                )
            return tuple(newly_applied)


async def _ledger_exists(session: AsyncSession) -> bool:
    return bool(await session.scalar(_LEDGER_EXISTS_STATEMENT))


async def _execute_sql(session: AsyncSession, sql: str) -> None:
    connection = await session.connection()
    raw_connection = await connection.get_raw_connection()
    await raw_connection.driver_connection.execute(sql)


def _validate_existing(
    existing: AppliedMigration, artifact: MigrationArtifact
) -> None:
    if (
        existing.path != artifact.path
        or existing.checksum != artifact.checksum
    ):
        raise ValueError("migration version is already recorded with a different artifact")
