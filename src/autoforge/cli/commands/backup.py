import asyncio
import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from autoforge.core.backup import BackupArtifact, BackupArtifactKind, S3StorageConfig
from autoforge.infrastructure.backup import (
    Aioboto3S3Client,
    S3CompatibleBackupTransfer,
)
from autoforge.infrastructure.secret import EnvironmentSecretProvider

app = typer.Typer()


@app.callback(invoke_without_command=True)
def backup(
    source: Annotated[Path, typer.Option(exists=True, file_okay=True, dir_okay=False)],
    name: Annotated[str, typer.Option("--name")],
    kind: Annotated[str, typer.Option("--kind")] = "log",
) -> None:
    """Upload one generated-backup artifact and verify its remote checksum."""

    try:
        artifact_kind = BackupArtifactKind(kind)
    except ValueError as error:
        raise typer.BadParameter("kind must be log or postgres_dump") from error

    try:
        object_id = asyncio.run(_transfer(source, name, artifact_kind))
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Verified backup artifact: {object_id}")


async def _transfer(
    source: Path, name: str, kind: BackupArtifactKind
) -> str:
    digest = hashlib.sha256()
    with source.open("rb") as file_object:
        for chunk in iter(lambda: file_object.read(1024 * 1024), b""):
            digest.update(chunk)
    artifact = BackupArtifact(
        kind=kind,
        name=name,
        size_bytes=source.stat().st_size,
        created_at=datetime.now(UTC),
        sha256=digest.hexdigest(),
    )
    configuration = S3StorageConfig.from_environment(os.environ)
    provider = EnvironmentSecretProvider(
        secret_names={
            "S3_ACCESS_KEY": "S3_ACCESS_KEY",
            "S3_SECRET_KEY": "S3_SECRET_KEY",
        }
    )
    async with Aioboto3S3Client(
        configuration, secret_provider=provider
    ) as client:
        transfer = S3CompatibleBackupTransfer(configuration, client)
        object_id = await transfer.put(artifact, source=source)
        await transfer.verify(object_id, expected_sha256=artifact.sha256)
        return object_id
