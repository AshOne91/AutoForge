from pathlib import Path

import pytest
import typer
import yaml
from pytest import MonkeyPatch
from typer.testing import CliRunner

from autoforge import __version__
from autoforge.cli.app import app
from autoforge.cli.commands.generate import (
    _validate_database_placements,
    _validate_endpoint_dependencies,
)
from autoforge.core.specification import ModuleSpec, ProjectSpec

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
    assert "Generated and validated 2 units" in first.output
    assert (output / "src/sample/main.py").is_file()
    assert (output / ".autoforge/manifest.json").is_file()


def test_generate_rejects_session_dependency_without_service(tmp_path: Path) -> None:
    project = tmp_path / "autoforge.yaml"
    specifications = tmp_path / "specifications"
    output = tmp_path / "output"
    specifications.mkdir()
    project.write_text(
        'spec_version: "1"\nproject:\n  name: Sample\n'
        '  package_name: sample\n  version: "0.1.0"\n'
        "application:\n  modules: [identity]\n",
        encoding="utf-8",
    )
    (specifications / "identity.yaml").write_text(
        'spec_version: "1"\nmodule:\n  name: identity\n'
        "  display_name: Identity\n  route_prefix: /identity\n"
        "endpoints:\n  - name: login\n    method: POST\n"
        "    path: /login\n    response:\n      fields: []\n"
        "    handler: login\n    dependencies: [session_store]\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "generate",
            "--project",
            str(project),
            "--specifications",
            str(specifications),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code != 0
    assert not output.exists()

    project_spec = ProjectSpec.model_validate(
        yaml.safe_load(project.read_text(encoding="utf-8"))
    )
    module_spec = ModuleSpec.model_validate(
        yaml.safe_load(
            (specifications / "identity.yaml").read_text(encoding="utf-8")
        )
    )
    with pytest.raises(typer.BadParameter, match="requires a redis_session service"):
        _validate_endpoint_dependencies(project_spec, [module_spec])


def test_current_session_dependency_requires_session_service() -> None:
    project_spec = ProjectSpec.model_validate(
        {
            "spec_version": "1",
            "project": {
                "name": "Sample",
                "package_name": "sample",
                "version": "0.1.0",
            },
            "application": {},
        }
    )
    module_spec = ModuleSpec.model_validate(
        {
            "spec_version": "1",
            "module": {
                "name": "account",
                "display_name": "Account",
                "route_prefix": "/account",
            },
            "endpoints": [
                {
                    "name": "profile",
                    "method": "GET",
                    "path": "/profile",
                    "response": {"fields": []},
                    "handler": "profile",
                    "dependencies": ["current_session"],
                }
            ],
        }
    )

    with pytest.raises(typer.BadParameter, match="requires a redis_session service"):
        _validate_endpoint_dependencies(project_spec, [module_spec])


def test_plugin_reports_unavailable_command() -> None:
    result = runner.invoke(app, ["plugin"])

    assert result.exit_code == 1
    assert "PluginLoader 구현 이후" in result.output


def test_generate_rejects_undeclared_database_placement_store() -> None:
    project_spec = ProjectSpec.model_validate(
        {
            "spec_version": "1",
            "project": {
                "name": "Sample",
                "package_name": "sample",
                "version": "0.1.0",
            },
            "application": {
                "databases": [
                    {"name": "account", "global_url_env": "ACCOUNT_URL"}
                ]
            },
        }
    )
    module_spec = ModuleSpec.model_validate(
        {
            "spec_version": "1",
            "module": {
                "name": "profile",
                "display_name": "Profile",
                "route_prefix": "/profile",
            },
            "database": {
                "provider": "agnostic",
                "tables": [
                    {
                        "name": "profiles",
                        "columns": [
                            {
                                "name": "id",
                                "type": {"kind": "uuid"},
                                "primary_key": True,
                            }
                        ],
                    }
                ],
                "placements": [
                    {
                        "table": "profiles",
                        "store": "missing",
                        "mode": "global",
                    }
                ],
            },
        }
    )

    with pytest.raises(typer.BadParameter, match="undeclared stores: missing"):
        _validate_database_placements(project_spec, [module_spec])
