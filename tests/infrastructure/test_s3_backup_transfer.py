from datetime import UTC, datetime
from pathlib import Path

import pytest

from autoforge.core.backup import BackupArtifact, BackupArtifactKind, S3StorageConfig
from autoforge.infrastructure.backup import S3CompatibleBackupTransfer


class FakeS3Client:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, object]] = []
        self.verify_calls: list[tuple[str, str]] = []

    async def put_file(self, **kwargs: object) -> str:
        self.put_calls.append(kwargs)
        return "minio://backups/logs/app.log"

    async def verify_object(self, object_id: str, *, expected_sha256: str) -> None:
        self.verify_calls.append((object_id, expected_sha256))


def _artifact(size_bytes: int = 4) -> BackupArtifact:
    return BackupArtifact(
        kind=BackupArtifactKind.LOG,
        name="logs/app.log",
        size_bytes=size_bytes,
        created_at=datetime.now(UTC),
        sha256="a" * 64,
    )


@pytest.mark.anyio
async def test_s3_transfer_injects_config_and_object_key(tmp_path: Path) -> None:
    source = tmp_path / "app.log"
    source.write_bytes(b"data")
    client = FakeS3Client()
    transfer = S3CompatibleBackupTransfer(
        S3StorageConfig(endpoint="http://minio:9000", bucket="backups", prefix="autoforge"),
        client,
    )

    object_id = await transfer.put(_artifact(), source=source)
    await transfer.verify(object_id, expected_sha256="a" * 64)

    assert object_id.startswith("minio://")
    assert client.put_calls[0]["key"] == "autoforge/logs/app.log"
    assert client.put_calls[0]["expected_sha256"] == "a" * 64
    assert client.verify_calls == [(object_id, "a" * 64)]


@pytest.mark.anyio
async def test_s3_transfer_rejects_manifest_size_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "app.log"
    source.write_bytes(b"data")
    transfer = S3CompatibleBackupTransfer(
        S3StorageConfig(endpoint="http://minio:9000", bucket="backups"),
        FakeS3Client(),
    )

    with pytest.raises(ValueError, match="size"):
        await transfer.put(_artifact(size_bytes=3), source=source)
