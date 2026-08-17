from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
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
COMPOSE_TIMEOUT_SECONDS = 180


def _project_specification(*, mysql_mode: str = "standalone") -> ProjectSpec:
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
                    "mysql_mode": mysql_mode,
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


def _generate(root: Path, *, mysql_mode: str) -> None:
    workspace = Workspace(root)
    runner = GenerationRunner()
    runner.run(
        job_id="mysql-runtime-project",
        specification=_project_specification(mysql_mode=mysql_mode),
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
            timeout=COMPOSE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            command,
            returncode=124,
            stdout="",
            stderr=(
                "docker compose exceeded "
                f"{COMPOSE_TIMEOUT_SECONDS} seconds"
            ),
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


def _retry(
    operation: Callable[[], subprocess.CompletedProcess[str]], action: str
) -> subprocess.CompletedProcess[str]:
    result = operation()
    for _ in range(29):
        if result.returncode == 0:
            return result
        time.sleep(2)
        result = operation()
    _check(result, action)
    raise AssertionError("unreachable")


def _mysql_query(
    root: Path, *, mysql_mode: str, query: str
) -> subprocess.CompletedProcess[str]:
    return _compose(
        root,
        "exec",
        "-T",
        "mysql",
        "mysql",
        "-h",
        "127.0.0.1",
        "-P",
        "6446" if mysql_mode == "ha" else "3306",
        "-uautoforge",
        "-pchange-me",
        "-D",
        "identity",
        "-e",
        query,
    )


def _application_health(root: Path) -> subprocess.CompletedProcess[str]:
    return _compose(
        root,
        "exec",
        "-T",
        "application",
        "python",
        "-c",
        "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8000/health').status == 200",
    )


def _verify_generated_application(root: Path) -> None:
    LOGGER.info("starting generated application")
    _check(
        _compose(root, "up", "-d", "--no-deps", "application"),
        "generated application startup",
    )
    _retry(lambda: _application_health(root), "generated application health")


def _verify_mysql_ha_failover(root: Path) -> None:
    LOGGER.info("stopping generated MySQL HA primary")
    _check(_compose(root, "stop", "mysql-ha-0"), "MySQL HA primary stop")
    try:
        LOGGER.info("checking Router writer after primary failover")
        result = _retry(
            lambda: _mysql_query(
                root,
                mysql_mode="ha",
                query=(
                    "INSERT INTO login_accounts (user_id, email, is_active) "
                    "VALUES ('00000000-0000-0000-0000-000000000001', "
                    "'autoforge-ha-probe@example.invalid', TRUE) "
                    "ON DUPLICATE KEY UPDATE is_active = VALUES(is_active); "
                    "SELECT @@hostname AS writer_host, @@read_only AS writer_read_only;"
                ),
            ),
            "MySQL HA Router writer after primary failover",
        )
        if "\t0" not in result.stdout:
            raise RuntimeError("MySQL HA Router did not reach a writable primary")
        _retry(
            lambda: _application_health(root),
            "generated application health after MySQL HA failover",
        )
    finally:
        LOGGER.info("restarting generated MySQL HA primary")
        _check(_compose(root, "start", "mysql-ha-0"), "MySQL HA primary restart")

    LOGGER.info("checking generated MySQL HA cluster rejoin")
    _retry(
        lambda: _compose(
            root,
            "exec",
            "-T",
            "mysql-ha-1",
            "mysqlsh",
            "--no-wizard",
            "--js",
            "--uri",
            "autoforge_cluster:change-me-cluster@127.0.0.1:3306",
            "-e",
            "const status = dba.getCluster().status(); "
            "if (status.defaultReplicaSet.status !== 'OK') "
            "throw new Error(JSON.stringify(status));",
        ),
        "MySQL HA cluster rejoin",
    )


def _verify(root: Path, *, mysql_mode: str) -> None:
    LOGGER.info("checking generated Compose configuration")
    _check(_compose(root, "config", "--quiet"), "Compose configuration")
    LOGGER.info("building generated migration image")
    _check(_compose(root, "build", "migrate"), "generated image build")
    LOGGER.info("starting generated MySQL services")
    _check(_compose(root, "up", "-d", "mysql-init"), "MySQL startup")
    LOGGER.info("running generated migration")
    _check(
        _compose(root, "run", "--rm", "--no-deps", "migrate"),
        "generated migration",
    )
    LOGGER.info("checking generated schema")
    result = _mysql_query(
        root,
        mysql_mode=mysql_mode,
        query="SHOW TABLES; SELECT version_num FROM alembic_version;",
    )
    _check(result, "generated schema verification")
    if "login_accounts" not in result.stdout or "af_identity_identity_0001" not in result.stdout:
        raise RuntimeError(
            "generated schema verification did not find login_accounts and the Alembic version"
        )
    if mysql_mode == "ha":
        _verify_generated_application(root)
        _verify_mysql_ha_failover(root)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the opt-in generated MySQL runtime validation."
    )
    parser.add_argument("--mysql-mode", choices=("standalone", "ha"), default="standalone")
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    root_path = Path(tempfile.mkdtemp(prefix="autoforge-mysql-runtime-"))
    try:
        LOGGER.info("generating disposable MySQL project in %s", root_path)
        _generate(root_path, mysql_mode=arguments.mysql_mode)
        _verify(root_path, mysql_mode=arguments.mysql_mode)
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
