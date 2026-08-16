import asyncio
from pathlib import Path

import pytest

from autoforge.core.backup import S3StorageConfig
from autoforge.infrastructure.backup import Aioboto3S3Client


def test_aioboto3_client_requires_context_for_operations(tmp_path: Path) -> None:
    client = Aioboto3S3Client(
        S3StorageConfig(endpoint="http://minio:9000", bucket="backups")
    )

    with pytest.raises(RuntimeError, match="async context"):
        asyncio.run(
            client.put_file(
                bucket="backups",
                key="app.log",
                source=tmp_path / "missing.log",
                expected_sha256="a" * 64,
            )
        )
