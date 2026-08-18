from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from autoforge.cli.app import app
from autoforge.cli.commands import migrate_control_plane as migration_command

runner = CliRunner()


def test_migrate_control_plane_requires_database_url_environment(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTOFORGE_DATABASE_URL", raising=False)

    result = runner.invoke(
        app,
        ["migrate-control-plane", "--migration-directory", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert "AUTOFORGE_DATABASE_URL" in result.output
    assert "Traceback" not in result.output


def test_migrate_control_plane_emits_only_applied_versions(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def run_migrations(
        *, database_url: str, migration_directory: Path
    ) -> tuple[int, ...]:
        captured["database_url"] = database_url
        captured["migration_directory"] = migration_directory
        return (1, 7)

    monkeypatch.setattr(migration_command, "_run_migrations", run_migrations)

    result = runner.invoke(
        app,
        ["migrate-control-plane", "--migration-directory", str(tmp_path)],
        env={"AUTOFORGE_DATABASE_URL": "postgresql+asyncpg://user:secret@db/autoforge"},
    )

    assert result.exit_code == 0
    assert result.output == "1\n7\n"
    assert captured["migration_directory"] == tmp_path
    assert "secret" not in result.output
