from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from autoforge import __version__
from autoforge.cli.app import app

runner = CliRunner()


def test_version_works_without_project_config_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"AutoForge v{__version__}"


def test_generate_reports_unavailable_command() -> None:
    result = runner.invoke(app, ["generate"])

    assert result.exit_code == 1
    assert "Workspace 적용 단계 이후" in result.output


def test_plugin_reports_unavailable_command() -> None:
    result = runner.invoke(app, ["plugin"])

    assert result.exit_code == 1
    assert "PluginLoader 구현 이후" in result.output
