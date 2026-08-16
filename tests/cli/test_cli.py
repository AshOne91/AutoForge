from pathlib import Path
from typing import Self

import pytest
import typer
import yaml
from pytest import MonkeyPatch
from typer.testing import CliRunner

from autoforge import __version__
from autoforge.application.generation import (
    GenerationJobPipeline,
    GenerationValidationError,
)
from autoforge.cli.app import app
from autoforge.cli.commands import backup as backup_command
from autoforge.cli.commands.generate import (
    _validate_database_placements,
    _validate_endpoint_dependencies,
)
from autoforge.core.pipeline import PipelineExecutionError
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


def test_backup_reports_invalid_kind(tmp_path: Path) -> None:
    source = tmp_path / "backup.log"
    source.write_text("backup", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "backup",
            "--source",
            str(source),
            "--name",
            "backup.log",
            "--kind",
            "invalid",
        ],
    )

    assert result.exit_code != 0
    assert "kind must be log or postgres_dump" in result.output


def test_backup_preflight_transfers_and_verifies_artifact(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    source = tmp_path / "backup.log"
    source.write_text("backup", encoding="utf-8")
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://minio:9000")
    monkeypatch.setenv("S3_BUCKET", "backups")
    monkeypatch.setenv("S3_PREFIX", "preflight")
    monkeypatch.setenv("S3_ACCESS_KEY", "autoforge")
    monkeypatch.setenv("S3_SECRET_KEY", "change-me")

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *exc_info: object) -> None:
            del exc_info

        async def put_file(self, **kwargs: object) -> str:
            assert kwargs["bucket"] == "backups"
            assert kwargs["key"] == "preflight/backup.log"
            return "s3://backups/preflight/backup.log"

        async def verify_object(
            self, object_id: str, *, expected_sha256: str
        ) -> None:
            assert object_id == "s3://backups/preflight/backup.log"
            assert len(expected_sha256) == 64

    monkeypatch.setattr(backup_command, "Aioboto3S3Client", FakeClient)
    result = runner.invoke(
        app,
        ["backup", "--source", str(source), "--name", "backup.log"],
    )

    assert result.exit_code == 0, result.output
    assert "Verified backup artifact: s3://backups/preflight/backup.log" in result.output


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


def test_generate_reports_pipeline_failure_without_internal_traceback(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    project = tmp_path / "autoforge.yaml"
    specifications = tmp_path / "specifications"
    specifications.mkdir()
    project.write_text("{}", encoding="utf-8")

    async def fail_pipeline(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PipelineExecutionError(
            "generation",
            "validate_generated_project",
            GenerationValidationError("validation failed at ruff"),
        )

    monkeypatch.setattr(GenerationJobPipeline, "run", fail_pipeline)

    result = runner.invoke(
        app,
        [
            "generate",
            "--project",
            str(project),
            "--specifications",
            str(specifications),
            "--output",
            str(tmp_path / "output"),
        ],
    )

    assert result.exit_code == 1
    assert "Error: validation failed at ruff" in result.output
    assert "Traceback" not in result.output


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
