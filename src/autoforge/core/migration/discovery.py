import re
from pathlib import Path

from autoforge.core.migration.models import MigrationArtifact, order_migrations

_MIGRATION_FILENAME = re.compile(r"(?P<version>0*[1-9]\d*)_(?P<name>.+)\.sql$")


def discover_migrations(directory: Path) -> tuple[MigrationArtifact, ...]:
    """Read direct UTF-8 SQL artifacts from one declared migration directory."""

    if not directory.is_dir():
        raise ValueError("migration directory must exist")
    artifacts: list[MigrationArtifact] = []
    for path in directory.iterdir():
        if path.suffix != ".sql":
            continue
        match = _MIGRATION_FILENAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"invalid migration filename: {path.name}")
        artifacts.append(
            MigrationArtifact(
                version=int(match["version"]),
                path=path.name,
                sql=path.read_text(encoding="utf-8"),
            )
        )
    return order_migrations(tuple(artifacts))
