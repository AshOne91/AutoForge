from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoforge.core.audit import AuditRecord
from autoforge.infrastructure.postgresql.control_plane import AuditRecordRow


class PostgreSQLAuditSink:
    """Idempotent envelope-only PostgreSQL audit sink."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def append(self, record: AuditRecord) -> None:
        statement = (
            insert(AuditRecordRow)
            .values(
                event_id=record.event_id,
                event_type=record.event_type,
                event_version=record.event_version,
                event_created_at=record.event_created_at,
                correlation_id=record.correlation_id,
                causation_id=record.causation_id,
                job_id=record.job_id,
                producer=record.producer,
                recorded_at=record.recorded_at,
                payload_redaction="envelope_only",
            )
            .on_conflict_do_nothing(index_elements=[AuditRecordRow.event_id])
        )
        async with self._sessions() as session, session.begin():
            await session.execute(statement)
