import json
from pathlib import PurePosixPath
from typing import Final

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
    specification_hash,
)
from autoforge.core.specification import ModuleSpec, ProjectSpec
from autoforge.services.generation.postgresql_ddl import PostgreSQLDDLGenerator

ALEMBIC_PROJECT_GENERATOR_ID: Final = "autoforge.generator.alembic.project"
ALEMBIC_BASELINE_GENERATOR_ID: Final = "autoforge.generator.alembic.baseline"
ALEMBIC_GENERATOR_VERSION: Final = "0.1.0"


class AlembicEnvironmentGenerator:
    @property
    def generator_id(self) -> str:
        return ALEMBIC_PROJECT_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return ALEMBIC_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        stores = specification.application.databases
        if not stores:
            return {}
        files: dict[PurePosixPath, str] = {
            PurePosixPath("alembic.ini"): self._render_ini(),
            PurePosixPath("scripts", "migrate.py"): self._render_runner(
                specification
            ),
        }
        for store in stores:
            root = PurePosixPath("migrations", store.name)
            files[root / "env.py"] = self._render_env()
            files[root / "script.py.mako"] = self._render_script_template()
        return files

    def plan(self, specification: ProjectSpec) -> GenerationPlan:
        rendered = self.render(specification)
        spec_hash = specification_hash(specification)
        return GenerationPlan(
            specification_version=specification.spec_version,
            specification_hash=spec_hash,
            files=[
                PlannedFile(
                    relative_path=path,
                    generator_id=self.generator_id,
                    generator_version=self.generator_version,
                    ownership=FileOwnership.GENERATED,
                    action=PlannedAction.CREATE,
                    specification_hash=spec_hash,
                    expected_content_hash=content_hash(content),
                    source="project:alembic-environment",
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _render_ini() -> str:
        return (
            "[alembic]\n"
            "prepend_sys_path = .\n"
            "path_separator = os\n"
            "\n"
            "[loggers]\n"
            "keys = root,sqlalchemy,alembic\n"
            "\n"
            "[handlers]\n"
            "keys = console\n"
            "\n"
            "[formatters]\n"
            "keys = generic\n"
            "\n"
            "[logger_root]\n"
            "level = WARN\n"
            "handlers = console\n"
            "qualname =\n"
            "\n"
            "[logger_sqlalchemy]\n"
            "level = WARN\n"
            "handlers =\n"
            "qualname = sqlalchemy.engine\n"
            "\n"
            "[logger_alembic]\n"
            "level = INFO\n"
            "handlers =\n"
            "qualname = alembic\n"
            "\n"
            "[handler_console]\n"
            "class = StreamHandler\n"
            "args = (sys.stderr,)\n"
            "level = NOTSET\n"
            "formatter = generic\n"
            "\n"
            "[formatter_generic]\n"
            "format = %(levelname)-5.5s [%(name)s] %(message)s\n"
        )

    @staticmethod
    def _render_env() -> str:
        return (
            "from asyncio import run\n"
            "from logging.config import fileConfig\n"
            "\n"
            "from alembic import context\n"
            "from sqlalchemy import pool\n"
            "from sqlalchemy.ext.asyncio import async_engine_from_config\n"
            "\n"
            "config = context.config\n"
            "if config.config_file_name is not None:\n"
            "    fileConfig(config.config_file_name)\n"
            "target_metadata = None\n"
            "\n"
            "\n"
            "def run_migrations_offline() -> None:\n"
            "    context.configure(\n"
            "        url=config.get_main_option('sqlalchemy.url'),\n"
            "        target_metadata=target_metadata,\n"
            "        literal_binds=True,\n"
            "        dialect_opts={'paramstyle': 'named'},\n"
            "    )\n"
            "    with context.begin_transaction():\n"
            "        context.run_migrations()\n"
            "\n"
            "\n"
            "def do_run_migrations(connection: object) -> None:\n"
            "    context.configure(connection=connection, target_metadata=target_metadata)\n"
            "    with context.begin_transaction():\n"
            "        context.run_migrations()\n"
            "\n"
            "\n"
            "async def run_migrations_online() -> None:\n"
            "    connectable = async_engine_from_config(\n"
            "        config.get_section(config.config_ini_section, {}),\n"
            "        prefix='sqlalchemy.',\n"
            "        poolclass=pool.NullPool,\n"
            "    )\n"
            "    async with connectable.connect() as connection:\n"
            "        await connection.run_sync(do_run_migrations)\n"
            "    await connectable.dispose()\n"
            "\n"
            "\n"
            "if context.is_offline_mode():\n"
            "    run_migrations_offline()\n"
            "else:\n"
            "    run(run_migrations_online())\n"
        )

    @staticmethod
    def _render_script_template() -> str:
        return (
            '"""${message}\n\nRevision ID: ${up_revision}\n"""\n'
            "from alembic import op\n"
            "import sqlalchemy as sa\n"
            "${imports if imports else ''}\n"
            "\n"
            "revision = ${repr(up_revision)}\n"
            "down_revision = ${repr(down_revision)}\n"
            "branch_labels = ${repr(branch_labels)}\n"
            "depends_on = ${repr(depends_on)}\n"
            "\n"
            "\n"
            "def upgrade() -> None:\n"
            "    ${upgrades if upgrades else 'pass'}\n"
            "\n"
            "\n"
            "def downgrade() -> None:\n"
            "    ${downgrades if downgrades else 'pass'}\n"
        )

    @staticmethod
    def _render_runner(specification: ProjectSpec) -> str:
        targets = [
            (store.name, environment_name)
            for store in specification.application.databases
            for environment_name in (
                [store.global_url_env] if store.global_url_env is not None else []
            )
            + [shard.url_env for shard in store.shards]
        ]
        targets_literal = json.dumps(targets, ensure_ascii=False)
        return (
            "from __future__ import annotations\n"
            "\n"
            "import os\n"
            "\n"
            "from alembic import command\n"
            "from alembic.config import Config\n"
            "\n"
            f"from {specification.project.package_name}.application.observability import (\n"
            "    LOGGER,\n"
            "    configure_logging,\n"
            ")\n"
            "\n"
            f"DATABASE_TARGETS = {targets_literal}\n"
            "\n"
            "\n"
            "def migrate(store: str, environment_name: str) -> None:\n"
            "    url = os.environ.get(environment_name)\n"
            "    if not url:\n"
            "        raise RuntimeError(\n"
            "            f'Required environment variable is missing: {environment_name}'\n"
            "        )\n"
            "    config = Config('alembic.ini')\n"
            "    config.set_main_option('script_location', f'migrations/{store}')\n"
            "    config.set_main_option('sqlalchemy.url', url.replace('%', '%%'))\n"
            "    command.upgrade(config, 'heads')\n"
            "\n"
            "\n"
            "def main() -> None:\n"
            "    configure_logging()\n"
            "    for store, environment_name in DATABASE_TARGETS:\n"
            "        LOGGER.info('migration starting', extra={'store': store})\n"
            "        migrate(store, environment_name)\n"
            "\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )


class AlembicBaselineGenerator:
    def __init__(self) -> None:
        self._ddl = PostgreSQLDDLGenerator()

    @property
    def generator_id(self) -> str:
        return ALEMBIC_BASELINE_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return ALEMBIC_GENERATOR_VERSION

    def render(self, specification: ModuleSpec) -> dict[PurePosixPath, str]:
        database = specification.database
        if database is None:
            return {}
        stores = sorted({placement.store for placement in database.placements})
        rendered: dict[PurePosixPath, str] = {}
        for store in stores:
            statements, tables = self._ddl.statements_for_store(
                specification, store
            )
            if not statements:
                continue
            path = PurePosixPath(
                "migrations",
                store,
                "versions",
                f"0001_{specification.module.name}.py",
            )
            rendered[path] = self._render_revision(
                module=specification.module.name,
                store=store,
                statements=statements,
                tables=tables,
            )
        return rendered

    def plan(self, specification: ModuleSpec) -> GenerationPlan:
        rendered = self.render(specification)
        spec_hash = specification_hash(specification)
        return GenerationPlan(
            specification_version=specification.spec_version,
            specification_hash=spec_hash,
            files=[
                PlannedFile(
                    relative_path=path,
                    generator_id=self.generator_id,
                    generator_version=self.generator_version,
                    ownership=FileOwnership.SCAFFOLDED,
                    action=PlannedAction.CREATE,
                    specification_hash=spec_hash,
                    expected_content_hash=content_hash(content),
                    source=f"module:{specification.module.name}:alembic-baseline",
                )
                for path, content in sorted(
                    rendered.items(), key=lambda item: item[0].as_posix()
                )
            ],
        )

    @staticmethod
    def _render_revision(
        *,
        module: str,
        store: str,
        statements: list[str],
        tables: list[str],
    ) -> str:
        revision = f"af_{store}_{module}_0001"
        execute_lines = "\n".join(
            f"    op.execute({statement!r})" for statement in statements
        )
        downgrade_lines = "\n".join(
            f"    op.execute('DROP TABLE IF EXISTS {table} CASCADE')"
            for table in reversed(tables)
        )
        return (
            f'"""AutoForge baseline for {module} in {store}."""\n'
            "\n"
            "from alembic import op\n"
            "\n"
            f"revision = {revision!r}\n"
            "down_revision = None\n"
            "branch_labels = None\n"
            "depends_on = None\n"
            "\n"
            "\n"
            "def upgrade() -> None:\n"
            f"{execute_lines}\n"
            "\n"
            "\n"
            "def downgrade() -> None:\n"
            f"{downgrade_lines}\n"
        )
