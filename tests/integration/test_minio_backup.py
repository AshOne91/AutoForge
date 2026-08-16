import hashlib
import importlib.util
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from autoforge.core.backup import BackupArtifact, BackupArtifactKind, S3StorageConfig
from autoforge.core.secret import SecretReference
from autoforge.infrastructure.backup import (
    Aioboto3S3Client,
    S3CompatibleBackupTransfer,
)
from autoforge.infrastructure.secret import EnvironmentSecretProvider

pytestmark = pytest.mark.integration


def _configured() -> bool:
    return bool(
        os.getenv("AUTOFORGE_MINIO_ENDPOINT")
        and os.getenv("AUTOFORGE_MINIO_BUCKET")
        and os.getenv("AUTOFORGE_MINIO_ACCESS_KEY")
        and os.getenv("AUTOFORGE_MINIO_SECRET_KEY")
        and importlib.util.find_spec("aioboto3")
    )


@pytest.mark.anyio
async def test_minio_backup_round_trip(tmp_path: Path) -> None:
    if not _configured():
        pytest.skip("MinIO endpoint, credentials, and aioboto3 are not configured")

    source = tmp_path / "integration.log"
    source.write_bytes(b"autoforge-minio-integration")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    configuration = S3StorageConfig(
        endpoint=os.environ["AUTOFORGE_MINIO_ENDPOINT"],
        bucket=os.environ["AUTOFORGE_MINIO_BUCKET"],
        prefix="autoforge-integration",
        access_key_id=SecretReference("minio/access-key"),
        secret_access_key=SecretReference("minio/secret-key"),
    )
    provider = EnvironmentSecretProvider(
        secret_names={
            "minio/access-key": "AUTOFORGE_MINIO_ACCESS_KEY",
            "minio/secret-key": "AUTOFORGE_MINIO_SECRET_KEY",
        }
    )
    artifact = BackupArtifact(
        kind=BackupArtifactKind.LOG,
        name="integration.log",
        size_bytes=source.stat().st_size,
        created_at=datetime.now(UTC),
        sha256=digest,
    )

    async with Aioboto3S3Client(
        configuration, secret_provider=provider
    ) as client:
        transfer = S3CompatibleBackupTransfer(configuration, client)
        object_id = await transfer.put(artifact, source=source)
        await transfer.verify(object_id, expected_sha256=digest)
