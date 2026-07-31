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


def test_generate_applies_specs_and_supports_repeated_run(tmp_path: Path) -> None:
    project = tmp_path / "autoforge.yaml"
    specifications = tmp_path / "specifications"
    output = tmp_path / "output"
    specifications.mkdir()
    project.write_text(
        'spec_version: "1"\nproject:\n  name: Sample\n'
        '  package_name: sample\n  version: "0.1.0"\n'
        "application:\n  modules: [account]\n",
        encoding="utf-8",
    )
    (specifications / "account.yaml").write_text(
        'spec_version: "1"\nmodule:\n  name: account\n'
        "  display_name: Account\n  route_prefix: /api/account\n",
        encoding="utf-8",
    )
    arguments = ["generate", "--project", str(project), "--specifications", str(specifications), "--output", str(output)]

    first = runner.invoke(app, arguments)
    second = runner.invoke(app, arguments)

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert (output / "src/sample/main.py").is_file()
    assert (output / ".autoforge/manifest.json").is_file()


def test_plugin_reports_unavailable_command() -> None:
    result = runner.invoke(app, ["plugin"])

    assert result.exit_code == 1
    assert "PluginLoader 구현 이후" in result.output
