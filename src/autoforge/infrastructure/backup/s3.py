from __future__ import annotations

from pathlib import Path
from typing import Protocol

from autoforge.core.backup import BackupArtifact, S3StorageConfig


class AsyncS3ObjectClient(Protocol):
    """Small SDK-neutral client surface required by the backup adapter."""

    async def put_file(
        self,
        *,
        bucket: str,
        key: str,
        source: Path,
        expected_sha256: str,
    ) -> str: ...

    async def verify_object(
        self, object_id: str, *, expected_sha256: str
    ) -> None: ...


class S3CompatibleBackupTransfer:
    """BackupTransfer adapter backed by an injected async S3-compatible client."""

    def __init__(
        self, configuration: S3StorageConfig, client: AsyncS3ObjectClient
    ) -> None:
        self._configuration = configuration
        self._client = client

    @property
    def configuration(self) -> S3StorageConfig:
        return self._configuration

    async def put(self, artifact: BackupArtifact, *, source: Path) -> str:
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.stat().st_size != artifact.size_bytes:
            raise ValueError("backup source size does not match its manifest")
        return await self._client.put_file(
            bucket=self._configuration.bucket,
            key=self._object_key(artifact),
            source=source,
            expected_sha256=artifact.sha256,
        )

    async def verify(self, object_id: str, *, expected_sha256: str) -> None:
        await self._client.verify_object(
            object_id, expected_sha256=expected_sha256
        )

    def _object_key(self, artifact: BackupArtifact) -> str:
        name = artifact.name.as_posix()
        prefix = self._configuration.prefix
        return f"{prefix}/{name}" if prefix else name
