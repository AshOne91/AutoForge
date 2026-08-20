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
    DataPlacementMode,
    FieldTypeKind,
    ModuleSpec,
    TableSpec,
)

POSTGRESQL_DDL_GENERATOR_ID: Final = "autoforge.generator.postgresql-ddl"
POSTGRESQL_DDL_GENERATOR_VERSION: Final = "0.1.0"

_SQL_TYPES: Final = {
    FieldTypeKind.STRING: "TEXT",
    FieldTypeKind.INTEGER: "BIGINT",
    FieldTypeKind.NUMBER: "DOUBLE PRECISION",
    FieldTypeKind.BOOLEAN: "BOOLEAN",
    FieldTypeKind.DATETIME: "TIMESTAMPTZ",
    FieldTypeKind.UUID: "UUID",
}


class PostgreSQLDDLGenerator:
    """Generate deterministic PostgreSQL bootstrap migrations by placement."""

    @property
    def generator_id(self) -> str:
        return POSTGRESQL_DDL_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return POSTGRESQL_DDL_GENERATOR_VERSION

    def render(self, specification: ModuleSpec) -> dict[PurePosixPath, str]:
        database = specification.database
        if database is None or not database.tables:
            return {}
        if database.provider == "mysql":
            return {}

        placements = {placement.table: placement for placement in database.placements}
        missing = sorted(
            {table.name for table in database.tables} - placements.keys()
        )
        if missing:
            raise ValueError(
                "PostgreSQL DDL generation requires an explicit placement for: "
                + ", ".join(missing)
            )

        migrated_tables = {
            table_name
            for migration in database.migrations
            for table_name in migration.create_tables
        }
        migrated_columns = {
            (addition.table, addition.column.name)
            for migration in database.migrations
            for addition in migration.add_columns
        }
        grouped: dict[DataPlacementMode, list[TableSpec]] = {
            DataPlacementMode.GLOBAL: [],
            DataPlacementMode.SHARDED: [],
        }
        for table in database.tables:
            if table.name not in migrated_tables:
                grouped[placements[table.name].mode].append(
                    table.model_copy(
                        update={
                            "columns": [
                                column
                                for column in table.columns
                                if (table.name, column.name) not in migrated_columns
                            ]
                        }
                    )
                )

        rendered: dict[PurePosixPath, str] = {}
        for mode, tables in grouped.items():
            if not tables:
                continue
            path = PurePosixPath(
                "database",
                mode.value,
                f"0001_{specification.module.name}.sql",
            )
            rendered[path] = self._render_migration(specification, mode, tables)
        for migration in database.migrations:
            statements: list[str] = []
            migration_tables = {table.name: table for table in database.tables}
            for table_name in migration.create_tables:
                table = migration_tables[table_name]
                statements.append(self._render_table(table))
                statements.extend(self._render_indexes(table))
            for addition in migration.add_columns:
                statements.append(
                    f"ALTER TABLE {addition.table} ADD COLUMN "
                    f"{self._render_column(addition.column)};\n"
                )
                if addition.column.index:
                    statements.append(
                        f"CREATE INDEX ix_{addition.table}_{addition.column.name} "
                        f"ON {addition.table} ({addition.column.name});\n"
                    )
            mode = placements[migration.create_tables[0] if migration.create_tables else migration.add_columns[0].table].mode
            path = PurePosixPath(
                "database",
                mode.value,
                f"{migration.revision:04d}_{specification.module.name}_{migration.name}.sql",
            )
            rendered[path] = self._render_statements(specification, mode, statements)
        return rendered

    def plan(self, specification: ModuleSpec) -> GenerationPlan:
        rendered_files = self.render(specification)
        spec_hash = specification_hash(specification)
        files = [
            PlannedFile(
                relative_path=path,
                generator_id=self.generator_id,
                generator_version=self.generator_version,
                ownership=FileOwnership.GENERATED,
                action=PlannedAction.CREATE,
                specification_hash=spec_hash,
                expected_content_hash=content_hash(content),
                source=f"module:{specification.module.name}:postgresql-ddl",
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

    def _render_migration(
        self,
        specification: ModuleSpec,
        mode: DataPlacementMode,
        tables: list[TableSpec],
    ) -> str:
        header = [
            "-- Generated by AutoForge. Do not edit manually.",
            f"-- Module: {specification.module.name}",
            f"-- Placement: {mode.value}",
            "",
        ]
        statements: list[str] = []
        for table in tables:
            statements.append(self._render_table(table))
            statements.extend(self._render_indexes(table))
        return "\n".join(header + statements).rstrip() + "\n"

    def _render_statements(
        self,
        specification: ModuleSpec,
        mode: DataPlacementMode,
        statements: list[str],
    ) -> str:
        header = [
            "-- Generated by AutoForge. Do not edit manually.",
            f"-- Module: {specification.module.name}",
            f"-- Placement: {mode.value}",
            "",
        ]
        return "\n".join(header + statements).rstrip() + "\n"

    def statements_for_store(
        self,
        specification: ModuleSpec,
        store: str,
    ) -> tuple[list[str], list[str]]:
        database = specification.database
        if database is None:
            return [], []
        placements = {placement.table: placement for placement in database.placements}
        tables = [
            table
            for table in database.tables
            if placements.get(table.name) is not None
            and placements[table.name].store == store
        ]
        statements: list[str] = []
        for table in tables:
            statements.append(self._render_table(table).strip())
            statements.extend(statement.strip() for statement in self._render_indexes(table))
        return statements, [table.name for table in tables]

    def _render_table(self, table: TableSpec) -> str:
        columns = ",\n".join(
            f"    {self._render_column(column)}" for column in table.columns
        )
        return f"CREATE TABLE {table.name} (\n{columns}\n);\n"

    def _render_column(self, column: ColumnSpec) -> str:
        try:
            sql_type = _SQL_TYPES[column.type.kind]
        except KeyError as error:
            raise ValueError(
                f"Unsupported PostgreSQL column type: {column.type.kind.value}"
            ) from error

        parts = [column.name, sql_type]
        if column.primary_key:
            parts.append("PRIMARY KEY")
        if not column.nullable and not column.primary_key:
            parts.append("NOT NULL")
        if column.unique:
            parts.append("UNIQUE")
        if column.default is not None:
            parts.extend(("DEFAULT", self._render_default(column.default)))
        return " ".join(parts)

    @staticmethod
    def _render_default(value: object) -> str:
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, str):
            return "'" + value.replace("'", "''") + "'"
        raise ValueError(f"Unsupported PostgreSQL default value: {value!r}")

    @staticmethod
    def _render_indexes(table: TableSpec) -> list[str]:
        return [
            f"CREATE INDEX ix_{table.name}_{column.name} "
            f"ON {table.name} ({column.name});\n"
            for column in table.columns
            if column.index and not column.primary_key
        ]
