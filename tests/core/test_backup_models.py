from datetime import UTC, datetime
from pathlib import PurePosixPath

import pytest

from autoforge.core.backup import BackupArtifact, BackupArtifactKind


def test_backup_artifact_normalizes_metadata() -> None:
    artifact = BackupArtifact(
        kind=BackupArtifactKind.POSTGRES_DUMP,
        name="db/identity.dump",
        size_bytes=12,
        created_at=datetime(2026, 8, 16, 12, tzinfo=UTC),
        sha256="A" * 64,
    )

    assert artifact.name == PurePosixPath("db/identity.dump")
    assert artifact.sha256 == "a" * 64
    assert artifact.created_at.tzinfo is UTC


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "../identity.dump"),
        ("size_bytes", -1),
        ("created_at", datetime(2026, 8, 16, tzinfo=UTC).replace(tzinfo=None)),
        ("sha256", "not-a-checksum"),
    ],
)
def test_backup_artifact_rejects_invalid_metadata(field: str, value: object) -> None:
    values: dict[str, object] = {
        "kind": BackupArtifactKind.LOG,
        "name": "logs/api.log",
        "size_bytes": 0,
        "created_at": datetime(2026, 8, 16, tzinfo=UTC),
        "sha256": "b" * 64,
    }
    values[field] = value

    with pytest.raises(ValueError):
        BackupArtifact(**values)  # type: ignore[arg-type]
