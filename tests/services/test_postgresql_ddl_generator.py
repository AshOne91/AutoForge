from pathlib import PurePosixPath

import pytest

from autoforge.core.generation import FileOwnership, Generator
from autoforge.core.specification import (
    ColumnSpec,
    DatabaseSpec,
    DataPlacementMode,
    DataPlacementSpec,
    FieldType,
    FieldTypeKind,
    ModuleInfo,
    ModuleSpec,
    TableSpec,
)
from autoforge.services.generation import PostgreSQLDDLGenerator


def database_specification() -> ModuleSpec:
    return ModuleSpec(
        spec_version="1",
        module=ModuleInfo(
            name="identity",
            display_name="Identity",
            route_prefix="/api/identity",
        ),
        database=DatabaseSpec(
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
                ),
                TableSpec(
                    name="user_profiles",
                    columns=[
                        ColumnSpec(
                            name="user_id",
                            type=FieldType(kind=FieldTypeKind.UUID),
                            primary_key=True,
                        ),
                        ColumnSpec(
                            name="display_name",
                            type=FieldType(kind=FieldTypeKind.STRING),
                        ),
                    ],
                ),
            ],
            placements=[
                DataPlacementSpec(
                    table="login_accounts",
                    store="identity",
                    mode=DataPlacementMode.GLOBAL,
                ),
                DataPlacementSpec(
                    table="user_profiles",
                    store="profile",
                    mode=DataPlacementMode.SHARDED,
                    partition_key="user_id",
                ),
            ],
        ),
    )


def test_postgresql_ddl_generator_satisfies_protocol() -> None:
    generator: Generator[ModuleSpec] = PostgreSQLDDLGenerator()

    assert isinstance(generator, Generator)


def test_render_separates_global_and_sharded_sql() -> None:
    rendered = PostgreSQLDDLGenerator().render(database_specification())

    global_path = PurePosixPath("database/global/0001_identity.sql")
    sharded_path = PurePosixPath("database/sharded/0001_identity.sql")
    assert set(rendered) == {global_path, sharded_path}

    global_sql = rendered[global_path]
    assert "-- Placement: global" in global_sql
    assert "CREATE TABLE login_accounts" in global_sql
    assert "email TEXT NOT NULL UNIQUE" in global_sql
    assert "is_active BOOLEAN NOT NULL DEFAULT TRUE" in global_sql
    assert "CREATE INDEX ix_login_accounts_email" in global_sql
    assert "user_profiles" not in global_sql

    sharded_sql = rendered[sharded_path]
    assert "-- Placement: sharded" in sharded_sql
    assert "CREATE TABLE user_profiles" in sharded_sql
    assert "login_accounts" not in sharded_sql


def test_plan_marks_sql_as_generated() -> None:
    plan = PostgreSQLDDLGenerator().plan(database_specification())

    assert len(plan.files) == 2
    assert all(file.ownership is FileOwnership.GENERATED for file in plan.files)


def test_render_requires_explicit_placement() -> None:
    specification = database_specification()
    assert specification.database is not None
    specification.database.placements.clear()

    with pytest.raises(ValueError, match="explicit placement"):
        PostgreSQLDDLGenerator().render(specification)
