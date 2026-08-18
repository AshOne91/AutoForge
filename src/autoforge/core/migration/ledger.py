from typing import Protocol

from autoforge.core.migration.models import AppliedMigration, MigrationArtifact


class MigrationVersionLedger(Protocol):
    """Provider-neutral durable record of migrations applied successfully."""

    async def list_applied(self) -> tuple[AppliedMigration, ...]: ...

    async def record_applied(
        self, artifact: MigrationArtifact
    ) -> AppliedMigration: ...
