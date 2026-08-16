from pathlib import Path
from typing import Protocol

from autoforge.core.backup.models import BackupArtifact


class BackupTransfer(Protocol):
    """Provider-neutral seam for transferring verified backup bytes."""

    async def put(
        self, artifact: BackupArtifact, *, source: Path
    ) -> str: ...

    async def verify(self, object_id: str, *, expected_sha256: str) -> None: ...
