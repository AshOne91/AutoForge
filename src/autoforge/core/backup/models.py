from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath

from autoforge.core.workspace import validate_workspace_relative_path

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


class BackupArtifactKind(StrEnum):
    LOG = "log"
    POSTGRES_DUMP = "postgres_dump"


@dataclass(frozen=True, kw_only=True, slots=True)
class BackupArtifact:
    """Immutable metadata for one verified off-host backup artifact."""

    kind: BackupArtifactKind
    name: PurePosixPath | str
    size_bytes: int
    created_at: datetime
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "name", validate_workspace_relative_path(self.name)
        )
        if self.size_bytes < 0:
            raise ValueError("backup artifact size must not be negative")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("backup artifact created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("backup artifact sha256 must be 64 hexadecimal characters")
        object.__setattr__(self, "sha256", self.sha256.lower())
