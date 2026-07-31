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
from autoforge.core.specification import (
    ColumnSpec,
    FieldTypeKind,
    ModuleSpec,
    ProjectSpec,
    RepositorySpec,
    TableSpec,
)
from autoforge.core.specification.naming import validate_python_name

SQLALCHEMY_PROJECT_GENERATOR_ID: Final = (
    "autoforge.generator.sqlalchemy.infrastructure"
)
SQLALCHEMY_MODEL_GENERATOR_ID: Final = "autoforge.generator.sqlalchemy.model"
SQLALCHEMY_GENERATOR_VERSION: Final = "0.1.0"

_PYTHON_TYPES: Final = {
    FieldTypeKind.STRING: "str",
    FieldTypeKind.INTEGER: "int",
    FieldTypeKind.NUMBER: "float",
    FieldTypeKind.BOOLEAN: "bool",
    FieldTypeKind.DATETIME: "datetime",
    FieldTypeKind.UUID: "UUID",
}
_SQLALCHEMY_TYPES: Final = {
    FieldTypeKind.STRING: "Text",
    FieldTypeKind.INTEGER: "BigInteger",
    FieldTypeKind.NUMBER: "Float",
    FieldTypeKind.BOOLEAN: "Boolean",
    FieldTypeKind.DATETIME: "DateTime(timezone=True)",
    FieldTypeKind.UUID: "Uuid",
}


class SQLAlchemyInfrastructureGenerator:
    """Generate reusable async SQLAlchemy infrastructure without runtime state."""

    @property
    def generator_id(self) -> str:
        return SQLALCHEMY_PROJECT_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return SQLALCHEMY_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        package_name = specification.project.package_name
        root = PurePosixPath("src", package_name, "infrastructure")
        database_root = root / "database"
        return {
            root / "__init__.py": "",
            database_root / "__init__.py": "",
            database_root / "base.py": self._render_base(),
            database_root / "routing.py": self._render_routing(),
            database_root / "session.py": self._render_session(package_name),
        }

    def plan(self, specification: ProjectSpec) -> GenerationPlan:
        return _generated_plan(
            specification=specification,
            rendered_files=self.render(specification),
            generator_id=self.generator_id,
            generator_version=self.generator_version,
            source=f"project:{specification.project.package_name}:sqlalchemy",
        )

    @staticmethod
    def _render_base() -> str:
        return (
            "from sqlalchemy.orm import DeclarativeBase\n"
            "\n"
            "\n"
            "class Base(DeclarativeBase):\n"
            "    pass\n"
        )

    @staticmethod
    def _render_routing() -> str:
        return (
            "from dataclasses import dataclass\n"
            "from typing import Protocol\n"
            "\n"
            "\n"
            "class ShardRoutingError(RuntimeError):\n"
            "    pass\n"
            "\n"
            "\n"
            "@dataclass(frozen=True, slots=True)\n"
            "class ShardTarget:\n"
            "    store: str\n"
            "    shard_id: str | None = None\n"
            "\n"
            "    @property\n"
            "    def is_global(self) -> bool:\n"
            "        return self.shard_id is None\n"
            "\n"
            "\n"
            "class ShardRouter(Protocol):\n"
            "    async def resolve(\n"
            "        self, store: str, partition_key: object | None,\n"
            "    ) -> ShardTarget: ...\n"
        )

    @staticmethod
    def _render_session(package_name: str) -> str:
        return (
            "from collections.abc import AsyncIterator, Mapping\n"
            "from contextlib import asynccontextmanager\n"
            "\n"
            "from sqlalchemy.ext.asyncio import (\n"
            "    AsyncEngine,\n"
            "    AsyncSession,\n"
            "    async_sessionmaker,\n"
            ")\n"
            "\n"
            f"from {package_name}.infrastructure.database.routing import (\n"
            "    ShardRoutingError,\n"
            "    ShardTarget,\n"
            ")\n"
            "\n"
            "\n"
            "class AsyncSessionRegistry:\n"
            "    def __init__(\n"
            "        self,\n"
            "        global_engines: Mapping[str, AsyncEngine],\n"
            "        shard_engines: Mapping[tuple[str, str], AsyncEngine],\n"
            "    ) -> None:\n"
            "        self._global_engines = dict(global_engines)\n"
            "        self._shard_engines = dict(shard_engines)\n"
            "\n"
            "    @asynccontextmanager\n"
            "    async def session(\n"
            "        self, target: ShardTarget,\n"
            "    ) -> AsyncIterator[AsyncSession]:\n"
            "        engine = self._engine_for(target)\n"
            "        factory = async_sessionmaker(engine, expire_on_commit=False)\n"
            "        async with factory() as session:\n"
            "            async with session.begin():\n"
            "                yield session\n"
            "\n"
            "    def _engine_for(self, target: ShardTarget) -> AsyncEngine:\n"
            "        if target.is_global:\n"
            "            engine = self._global_engines.get(target.store)\n"
            "        else:\n"
            "            assert target.shard_id is not None\n"
            "            engine = self._shard_engines.get(\n"
            "                (target.store, target.shard_id)\n"
            "            )\n"
            "        if engine is None:\n"
            "            raise ShardRoutingError(\n"
            "                f\"Database engine is not configured: {target}\"\n"
            "            )\n"
            "        return engine\n"
        )


class SQLAlchemyModelGenerator:
    """Generate SQLAlchemy 2.x annotated records from ModuleSpec tables."""

    def __init__(self, package_name: str) -> None:
        self._package_name = validate_python_name(package_name)

    @property
    def generator_id(self) -> str:
        return SQLALCHEMY_MODEL_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return SQLALCHEMY_GENERATOR_VERSION

    def render(self, specification: ModuleSpec) -> dict[PurePosixPath, str]:
        database = specification.database
        if database is None or not database.tables:
            return {}

        records = self._record_names(specification)
        path = PurePosixPath(
            "src",
            self._package_name,
            "modules",
            specification.module.name,
            "generated",
            "sqlalchemy_models.py",
        )
        repository_path = path.with_name("sqlalchemy_repositories.py")
        return {
            path: self._render_models(database.tables, records),
            repository_path: self._render_repositories(
                specification,
                records,
            ),
        }

    def plan(self, specification: ModuleSpec) -> GenerationPlan:
        return _generated_plan(
            specification=specification,
            rendered_files=self.render(specification),
            generator_id=self.generator_id,
            generator_version=self.generator_version,
            source=f"module:{specification.module.name}:sqlalchemy-model",
        )

    @staticmethod
    def _record_names(specification: ModuleSpec) -> dict[str, str]:
        assert specification.database is not None
        by_table: dict[str, list[str]] = {}
        for repository in specification.database.repositories:
            by_table.setdefault(repository.table, []).append(repository.aggregate)

        records: dict[str, str] = {}
        for table in specification.database.tables:
            aggregates = sorted(set(by_table.get(table.name, [])))
            if len(aggregates) != 1:
                raise ValueError(
                    f"Table '{table.name}' requires exactly one aggregate mapping"
                )
            records[table.name] = f"{aggregates[0]}Record"
        return records

    def _render_models(
        self,
        tables: list[TableSpec],
        records: dict[str, str],
    ) -> str:
        kinds = {column.type.kind for table in tables for column in table.columns}
        sqlalchemy_imports = {_sqlalchemy_import(kind) for kind in kinds}
        if any(
            column.default is not None
            for table in tables
            for column in table.columns
        ):
            sqlalchemy_imports.add("text")
        imports = ["from __future__ import annotations", ""]
        if FieldTypeKind.DATETIME in kinds:
            imports.extend(("from datetime import datetime", ""))
        if FieldTypeKind.UUID in kinds:
            imports.extend(("from uuid import UUID", ""))
        imports.append(
            f"from sqlalchemy import {', '.join(sorted(sqlalchemy_imports))}"
        )
        imports.append("from sqlalchemy.orm import Mapped, mapped_column")
        imports.extend(
            (
                "",
                f"from {self._package_name}.infrastructure.database.base import Base",
            )
        )
        classes = [self._render_table(table, records[table.name]) for table in tables]
        return "\n".join(imports) + "\n\n\n" + "\n\n\n".join(classes) + "\n"

    def _render_repositories(
        self,
        specification: ModuleSpec,
        records: dict[str, str],
    ) -> str:
        assert specification.database is not None
        module_path = (
            f"{self._package_name}.modules.{specification.module.name}.generated"
        )
        aggregates = sorted(
            {repository.aggregate for repository in specification.database.repositories}
        )
        record_names = sorted(records.values())
        table_by_name = {
            table.name: table for table in specification.database.tables
        }
        key_kinds = {
            column.type.kind
            for repository in specification.database.repositories
            for column in table_by_name[repository.table].columns
            if column.primary_key
        }
        imports: list[str] = []
        if FieldTypeKind.DATETIME in key_kinds:
            imports.extend(("from datetime import datetime", ""))
        if FieldTypeKind.UUID in key_kinds:
            imports.extend(("from uuid import UUID", ""))
        imports.extend(
            (
                "from sqlalchemy.ext.asyncio import AsyncSession",
                "",
                f"from {module_path}.models import {', '.join(aggregates)}",
                f"from {module_path}.sqlalchemy_models import {', '.join(record_names)}",
            )
        )
        classes = [
            self._render_repository(
                repository=repository,
                table=table_by_name[repository.table],
                record_name=records[repository.table],
            )
            for repository in specification.database.repositories
        ]
        return "\n".join(imports) + "\n\n\n" + "\n\n\n".join(classes) + "\n"

    def _render_repository(
        self,
        *,
        repository: RepositorySpec,
        table: TableSpec,
        record_name: str,
    ) -> str:
        repository_name = repository.name
        aggregate = repository.aggregate
        operations = repository.operations
        primary_keys = [column for column in table.columns if column.primary_key]
        if len(primary_keys) != 1:
            raise ValueError(
                f"SQLAlchemy Repository '{repository_name}' requires one primary key"
            )
        primary_key = primary_keys[0]
        key_type = _PYTHON_TYPES[primary_key.type.kind]
        column_names = [column.name for column in table.columns]
        assignments = ",\n".join(
            f"            {name}=aggregate.{name}" for name in column_names
        )
        domain_assignments = ",\n".join(
            f"            {name}=record.{name}" for name in column_names
        )
        lines = [
            f"class SQLAlchemy{repository_name}:",
            "    def __init__(self, session: AsyncSession) -> None:",
            "        self._session = session",
        ]
        for operation in operations:
            if operation == "find_by_id":
                lines.extend(
                    (
                        "",
                        "    async def find_by_id(",
                        f"        self, {primary_key.name}: {key_type},",
                        f"    ) -> {aggregate} | None:",
                        "        record = await self._session.get(",
                        f"            {record_name}, {primary_key.name}",
                        "        )",
                        "        if record is None:",
                        "            return None",
                        f"        return {aggregate}(\n{domain_assignments}\n        )",
                    )
                )
            elif operation == "save":
                lines.extend(
                    (
                        "",
                        "    async def save(",
                        f"        self, aggregate: {aggregate},",
                        "    ) -> None:",
                        f"        record = {record_name}(\n{assignments}\n        )",
                        "        await self._session.merge(record)",
                    )
                )
        return "\n".join(lines)

    def _render_table(self, table: TableSpec, record_name: str) -> str:
        lines = [f"class {record_name}(Base):", f'    __tablename__ = "{table.name}"']
        for column in table.columns:
            lines.extend(("", f"    {self._render_column(column)}"))
        return "\n".join(lines)

    @staticmethod
    def _render_column(column: ColumnSpec) -> str:
        try:
            python_type = _PYTHON_TYPES[column.type.kind]
            sqlalchemy_type = _SQLALCHEMY_TYPES[column.type.kind]
        except KeyError as error:
            raise ValueError(
                f"Unsupported SQLAlchemy column type: {column.type.kind.value}"
            ) from error

        annotation = python_type if not column.nullable else f"{python_type} | None"
        arguments = [sqlalchemy_type]
        if column.primary_key:
            arguments.append("primary_key=True")
        else:
            arguments.append(f"nullable={column.nullable}")
        if column.unique:
            arguments.append("unique=True")
        if column.index:
            arguments.append("index=True")
        if column.default is not None:
            default = _sql_default(column.default)
            arguments.append(f"server_default=text({default!r})")
        return (
            f"{column.name}: Mapped[{annotation}] = "
            f"mapped_column({', '.join(arguments)})"
        )


def _sqlalchemy_import(kind: FieldTypeKind) -> str:
    try:
        rendered = _SQLALCHEMY_TYPES[kind]
    except KeyError as error:
        raise ValueError(
            f"Unsupported SQLAlchemy column type: {kind.value}"
        ) from error
    return rendered.split("(", maxsplit=1)[0]


def _sql_default(value: object) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise ValueError(f"Unsupported SQLAlchemy server default: {value!r}")


def _generated_plan(
    *,
    specification: ProjectSpec | ModuleSpec,
    rendered_files: dict[PurePosixPath, str],
    generator_id: str,
    generator_version: str,
    source: str,
) -> GenerationPlan:
    spec_hash = specification_hash(specification)
    files = [
        PlannedFile(
            relative_path=path,
            generator_id=generator_id,
            generator_version=generator_version,
            ownership=FileOwnership.GENERATED,
            action=PlannedAction.CREATE,
            specification_hash=spec_hash,
            expected_content_hash=content_hash(content),
            source=source,
        )
        for path, content in sorted(
            rendered_files.items(), key=lambda item: item[0].as_posix()
        )
    ]
    return GenerationPlan(
        specification_version=specification.spec_version,
        specification_hash=spec_hash,
        files=files,
    )
