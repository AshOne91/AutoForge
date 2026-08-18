from datetime import UTC, datetime

import pytest

from autoforge.core.migration import (
    AppliedMigration,
    MigrationArtifact,
    discover_migrations,
    order_migrations,
)


def migration(*, version: int, sql: str = "SELECT 1;") -> MigrationArtifact:
    return MigrationArtifact(
        version=version,
        path=f"deploy/postgresql/init/{version:03d}_example.sql",
        sql=sql,
    )


def test_order_migrations_sorts_versions_and_derives_checksum() -> None:
    first = migration(version=1, sql="SELECT 1;")

    assert [
        artifact.version for artifact in order_migrations((migration(version=2), first))
    ] == [1, 2]
    assert first.checksum == "17db4fd369edb9244b9f91d9aeed145c3d04ad8ba6e95d06247f07a63527d11a"


def test_order_migrations_rejects_duplicate_versions() -> None:
    with pytest.raises(ValueError, match="unique"):
        order_migrations((migration(version=1), migration(version=1, sql="SELECT 2;")))


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"version": 0}, "positive"),
        ({"path": "../001_example.sql"}, "\\.\\."),
        ({"path": "001_example.txt"}, "end with .sql"),
        ({"sql": "  "}, "must not be empty"),
    ],
)
def test_migration_artifact_rejects_invalid_contract(
    values: dict[str, object], message: str
) -> None:
    base: dict[str, object] = {
        "version": 1,
        "path": "001_example.sql",
        "sql": "SELECT 1;",
    }
    base.update(values)

    with pytest.raises(ValueError, match=message):
        MigrationArtifact(**base)  # type: ignore[arg-type]


def test_applied_migration_normalizes_persisted_evidence() -> None:
    applied = AppliedMigration(
        version=1,
        path="001_control_plane.sql",
        checksum="A" * 64,
        applied_at=datetime(2026, 8, 18, 12, tzinfo=UTC),
    )

    assert applied.checksum == "a" * 64
    assert applied.applied_at.tzinfo is UTC


def test_discover_migrations_orders_direct_sql_artifacts(tmp_path) -> None:
    (tmp_path / "002_second.sql").write_text("SELECT 2;", encoding="utf-8")
    (tmp_path / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    artifacts = discover_migrations(tmp_path)

    assert [artifact.version for artifact in artifacts] == [1, 2]
    assert artifacts[0].path.as_posix() == "001_first.sql"


@pytest.mark.parametrize("filename", ["migration.sql", "000_invalid.sql", "001_.sql"])
def test_discover_migrations_rejects_malformed_sql_filenames(
    tmp_path, filename: str
) -> None:
    (tmp_path / filename).write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid migration filename"):
        discover_migrations(tmp_path)


def test_discover_migrations_rejects_duplicate_versions(tmp_path) -> None:
    (tmp_path / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "001_second.sql").write_text("SELECT 2;", encoding="utf-8")

    with pytest.raises(ValueError, match="unique"):
        discover_migrations(tmp_path)
