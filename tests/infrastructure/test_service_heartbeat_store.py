import asyncio
from datetime import UTC, datetime, timedelta

from autoforge.core.heartbeat import ServiceHeartbeatReport
from autoforge.infrastructure.heartbeat import InMemoryServiceHeartbeatStore


def test_in_memory_service_heartbeat_store_expires_reports() -> None:
    now = datetime(2026, 8, 18, tzinfo=UTC)

    def clock() -> datetime:
        return now

    async def scenario() -> None:
        nonlocal now
        store = InMemoryServiceHeartbeatStore(clock=clock)
        report = ServiceHeartbeatReport(
            instance_id="worker-1",
            service_name="generation-worker",
            deployed_version="1.0.0",
            dependencies={"postgres": "ok"},
        )
        recorded = await store.record(report, ttl=timedelta(seconds=30))

        assert recorded.reported_at == now
        assert await store.list_active() == (recorded,)

        now += timedelta(seconds=30)
        assert await store.list_active() == ()

    asyncio.run(scenario())
