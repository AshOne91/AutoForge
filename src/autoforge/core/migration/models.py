from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import PurePosixPath

from autoforge.core.workspace import validate_workspace_relative_path

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True, kw_only=True, slots=True)
class MigrationArtifact:
    """One immutable, ordered SQL artifact supplied to a provider executor."""

    version: int
    path: PurePosixPath | str
    sql: str
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("migration version must be positive")
        object.__setattr__(self, "path", validate_workspace_relative_path(self.path))
        if self.path.suffix != ".sql":
            raise ValueError("migration path must end with .sql")
        if not self.sql.strip():
            raise ValueError("migration SQL must not be empty")
        object.__setattr__(
            self,
            "checksum",
            sha256(self.sql.encode("utf-8")).hexdigest(),
        )


@dataclass(frozen=True, kw_only=True, slots=True)
class AppliedMigration:
    """Durable ledger evidence written only after a migration succeeds."""

    version: int
    path: PurePosixPath | str
    checksum: str
    applied_at: datetime

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("migration version must be positive")
        object.__setattr__(self, "path", validate_workspace_relative_path(self.path))
        if self.path.suffix != ".sql":
            raise ValueError("migration path must end with .sql")
        if not _SHA256.fullmatch(self.checksum):
            raise ValueError("migration checksum must be 64 hexadecimal characters")
        object.__setattr__(self, "checksum", self.checksum.lower())
        if self.applied_at.tzinfo is None or self.applied_at.utcoffset() is None:
            raise ValueError("migration applied_at must be timezone-aware")
        object.__setattr__(self, "applied_at", self.applied_at.astimezone(UTC))


def order_migrations(
    artifacts: list[MigrationArtifact] | tuple[MigrationArtifact, ...],
) -> tuple[MigrationArtifact, ...]:
    """Return migrations in version order and reject ambiguous duplicate versions."""

    ordered = tuple(sorted(artifacts, key=lambda artifact: artifact.version))
    if len({artifact.version for artifact in ordered}) != len(ordered):
        raise ValueError("migration versions must be unique")
    return ordered
