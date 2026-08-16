from pathlib import Path

from autoforge.core.backup import BackupTransfer


class FakeBackupTransfer:
    async def put(self, artifact, *, source: Path) -> str:
        return f"memory://{artifact.name}"

    async def verify(self, object_id: str, *, expected_sha256: str) -> None:
        return None


def test_backup_transfer_seam_supports_provider_implementation() -> None:
    transfer: BackupTransfer = FakeBackupTransfer()

    assert transfer is not None
