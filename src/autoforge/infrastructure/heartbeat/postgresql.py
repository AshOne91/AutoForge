from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoforge.core.heartbeat import ServiceHeartbeat, ServiceHeartbeatReport
from autoforge.infrastructure.postgresql.control_plane import ServiceHeartbeatRecord


class PostgreSQLServiceHeartbeatStore:
    """PostgreSQL-backed heartbeat store using database time as the authority."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def record(
        self,
        report: ServiceHeartbeatReport,
        *,
        ttl: timedelta,
    ) -> ServiceHeartbeat:
        if ttl <= timedelta(0):
            raise ValueError("ttl must be positive")
        values = {
            "service_name": report.service_name,
            "instance_id": report.instance_id,
            "deployed_version": report.deployed_version,
            "dependency_summary": report.model_dump(mode="json")["dependencies"],
            "reported_at": func.now(),
            "expires_at": func.now() + ttl,
        }
        statement = insert(ServiceHeartbeatRecord).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=("service_name", "instance_id"),
            set_={
                "deployed_version": statement.excluded.deployed_version,
                "dependency_summary": statement.excluded.dependency_summary,
                "reported_at": func.now(),
                "expires_at": func.now() + ttl,
            },
        ).returning(ServiceHeartbeatRecord)
        async with self._sessions() as session, session.begin():
            record = (await session.execute(statement)).scalar_one()
        return _to_heartbeat(record)

    async def list_active(self) -> tuple[ServiceHeartbeat, ...]:
        statement = (
            select(ServiceHeartbeatRecord)
            .where(ServiceHeartbeatRecord.expires_at > func.now())
            .order_by(
                ServiceHeartbeatRecord.service_name,
                ServiceHeartbeatRecord.instance_id,
            )
        )
        async with self._sessions() as session:
            records = (await session.execute(statement)).scalars().all()
        return tuple(_to_heartbeat(record) for record in records)


def _to_heartbeat(record: ServiceHeartbeatRecord) -> ServiceHeartbeat:
    return ServiceHeartbeat(
        instance_id=record.instance_id,
        service_name=record.service_name,
        deployed_version=record.deployed_version,
        dependencies=record.dependency_summary,
        reported_at=record.reported_at,
        expires_at=record.expires_at,
    )
