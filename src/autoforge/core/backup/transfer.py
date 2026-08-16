from pathlib import Path
from typing import Protocol

from autoforge.core.backup.config import S3StorageConfig
from autoforge.core.backup.models import BackupArtifact


class BackupTransfer(Protocol):
    """Provider-neutral seam for transferring verified backup bytes."""

    @property
    def configuration(self) -> S3StorageConfig: ...

    async def put(
        self, artifact: BackupArtifact, *, source: Path
    ) -> str: ...

    async def verify(self, object_id: str, *, expected_sha256: str) -> None: ...
