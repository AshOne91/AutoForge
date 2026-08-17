from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from autoforge.core.specification import (
    ColumnSpec,
    DatabaseSpec,
    DataPlacementMode,
    DataPlacementSpec,
    FieldType,
    FieldTypeKind,
    ModuleInfo,
    ModuleSpec,
    ProjectSpec,
    TableSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.services.generation import (
    AlembicBaselineGenerator,
    AlembicEnvironmentGenerator,
    DockerfileGenerator,
    FastAPIModuleGenerator,
    FastAPIProjectGenerator,
    GenerationRunner,
    LocalEnvironmentGenerator,
    MySQLDDLGenerator,
    SQLAlchemyInfrastructureGenerator,
)

LOGGER = logging.getLogger("autoforge.mysql_runtime")
PROJECT_NAME = "autoforge-mysql-runtime-check"


def _project_specification() -> ProjectSpec:
    return ProjectSpec.model_validate(
        {
            "spec_version": "1",
            "project": {
                "name": "Generated MySQL Runtime Check",
                "package_name": "mysql_server",
                "version": "0.1.0",
            },
            "application": {
                "modules": ["identity"],
                "databases": [
                    {"name": "identity", "global_url_env": "IDENTITY_DATABASE_URL"}
                ],
            },
            "tooling": {
                "docker": {"enabled": True},
                "local_environment": {
                    "enabled": True,
                    "application_enabled": True,
                    "database_provider": "mysql",
                    "host_port_base": 49700,
                },
            },
        }
    )


def _module_specification() -> ModuleSpec:
    return ModuleSpec(
        spec_version="1",
        module=ModuleInfo(
            name="identity",
            display_name="Identity",
            route_prefix="/api/identity",
        ),
        database=DatabaseSpec(
            provider="mysql",
            tables=[
                TableSpec(
                    name="login_accounts",
                    columns=[
                        ColumnSpec(
                            name="user_id",
                            type=FieldType(kind=FieldTypeKind.UUID),
                            primary_key=True,
                        ),
                        ColumnSpec(
                            name="email",
                            type=FieldType(kind=FieldTypeKind.STRING),
                            unique=True,
                            index=True,
                        ),
                        ColumnSpec(
                            name="is_active",
                            type=FieldType(kind=FieldTypeKind.BOOLEAN),
                            default=True,
                        ),
                    ],
                )
            ],
            placements=[
                DataPlacementSpec(
                    table="login_accounts",
                    store="identity",
                    mode=DataPlacementMode.GLOBAL,
                )
            ],
        ),
    )


def _generate(root: Path) -> None:
    workspace = Workspace(root)
    runner = GenerationRunner()
    runner.run(
        job_id="mysql-runtime-project",
        specification=_project_specification(),
        generators=[
            FastAPIProjectGenerator(),
            DockerfileGenerator(),
            AlembicEnvironmentGenerator(),
            LocalEnvironmentGenerator(),
            SQLAlchemyInfrastructureGenerator(),
        ],
        workspace=workspace,
    )
    runner.run(
        job_id="mysql-runtime-module",
        specification=_module_specification(),
        generators=[
            FastAPIModuleGenerator("mysql_server"),
            MySQLDDLGenerator(),
            AlembicBaselineGenerator(),
        ],
        workspace=workspace,
    )
    shutil.copyfile(
        root / "environment" / ".env.example",
        root / "environment" / ".env",
    )


def _compose(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    command = (
        "docker",
        "compose",
        "--project-name",
        PROJECT_NAME,
        "--env-file",
        ".env",
        "-f",
        "compose.integration.yml",
        *arguments,
    )
    try:
        return subprocess.run(
            command,
            cwd=root / "environment",
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return subprocess.CompletedProcess(
            command,
            returncode=127,
            stdout="",
            stderr=str(error),
        )


def _check(result: subprocess.CompletedProcess[str], action: str) -> None:
    if result.returncode == 0:
        return
    details = (result.stdout + "\n" + result.stderr).strip()
    raise RuntimeError(f"{action} failed (exit {result.returncode}):\n{details}")


def _verify(root: Path) -> None:
    _check(_compose(root, "config", "--quiet"), "Compose configuration")
    _check(_compose(root, "build", "migrate"), "generated image build")
    _check(_compose(root, "up", "-d", "mysql", "mysql-init"), "MySQL startup")
    _check(_compose(root, "run", "--rm", "migrate"), "generated migration")
    result = _compose(
        root,
        "exec",
        "-T",
        "mysql",
        "mysql",
        "-uautoforge",
        "-pchange-me",
        "-D",
        "identity",
        "-e",
        "SHOW TABLES; SELECT version_num FROM alembic_version;",
    )
    _check(result, "generated schema verification")
    if "login_accounts" not in result.stdout or "af_identity_identity_0001" not in result.stdout:
        raise RuntimeError(
            "generated schema verification did not find login_accounts and the Alembic version"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the opt-in generated MySQL runtime validation."
    )
    parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    root_path = Path(tempfile.mkdtemp(prefix="autoforge-mysql-runtime-"))
    try:
        LOGGER.info("generating disposable MySQL project in %s", root_path)
        _generate(root_path)
        _verify(root_path)
        LOGGER.info("generated MySQL runtime validation passed")
        return 0
    finally:
        compose_file = root_path / "environment" / "compose.integration.yml"
        if compose_file.is_file():
            cleanup = _compose(root_path, "down", "-v", "--remove-orphans")
            if cleanup.returncode != 0:
                LOGGER.error("runtime cleanup failed: %s", cleanup.stderr.strip())
        shutil.rmtree(root_path, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
