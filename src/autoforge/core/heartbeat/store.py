from datetime import timedelta
from typing import Protocol

from autoforge.core.heartbeat.models import ServiceHeartbeat, ServiceHeartbeatReport


class ServiceHeartbeatStore(Protocol):
    async def record(
        self,
        report: ServiceHeartbeatReport,
        *,
        ttl: timedelta,
    ) -> ServiceHeartbeat: ...

    async def list_active(self) -> tuple[ServiceHeartbeat, ...]: ...
