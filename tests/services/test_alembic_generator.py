import ast
from pathlib import PurePosixPath

from autoforge.core.generation import FileOwnership
from autoforge.core.specification import (
    AddColumnMigrationSpec,
    ColumnSpec,
    DatabaseMigrationSpec,
    DataPlacementSpec,
    ModuleSpec,
    ProjectSpec,
    TableSpec,
)
from autoforge.core.specification.types import FieldType, FieldTypeKind
from autoforge.services.generation.alembic import (
    AlembicBaselineGenerator,
    AlembicEnvironmentGenerator,
)
from autoforge.services.generation.postgresql_ddl import PostgreSQLDDLGenerator


def project_specification() -> ProjectSpec:
    return ProjectSpec.model_validate(
        {
            "spec_version": "1",
            "project": {
                "name": "KIS",
                "package_name": "kis_server",
                "version": "0.1.0",
            },
            "application": {
                "databases": [
                    {"name": "identity", "global_url_env": "IDENTITY_URL"},
                    {
                        "name": "account",
                        "shards": [
                            {"shard_id": "1", "url_env": "ACCOUNT_1_URL"},
                            {"shard_id": "2", "url_env": "ACCOUNT_2_URL"},
                        ],
                    },
                ]
            },
        }
    )


def module_specification() -> ModuleSpec:
    return ModuleSpec.model_validate(
        {
            "spec_version": "1",
            "module": {
                "name": "identity",
                "display_name": "Identity",
                "route_prefix": "/identity",
            },
            "models": [
                {
                    "name": "LoginAccount",
                    "fields": [
                        {"name": "user_id", "type": {"kind": "uuid"}},
                    ],
                }
            ],
            "database": {
                "provider": "agnostic",
                "tables": [
                    {
                        "name": "login_accounts",
                        "columns": [
                            {
                                "name": "user_id",
                                "type": {"kind": "uuid"},
                                "primary_key": True,
                            }
                        ],
                    }
                ],
                "repositories": [
                    {
                        "name": "LoginAccountRepository",
                        "aggregate": "LoginAccount",
                        "table": "login_accounts",
                        "operations": ["find_by_id"],
                    }
                ],
                "placements": [
                    {
                        "table": "login_accounts",
                        "store": "identity",
                        "mode": "global",
                    }
                ],
            },
        }
    )


def test_environment_generator_creates_store_specific_async_runners() -> None:
    files = AlembicEnvironmentGenerator().render(project_specification())

    assert PurePosixPath("migrations/identity/env.py") in files
    assert PurePosixPath("migrations/account/env.py") in files
    runner = files[PurePosixPath("scripts/migrate.py")]
    ast.parse(runner)
    assert '["identity", "IDENTITY_URL"]' in runner
    assert '["account", "ACCOUNT_1_URL"]' in runner
    assert '["account", "ACCOUNT_2_URL"]' in runner
    assert "command.upgrade(config, 'heads')" in runner
    assert "configure_logging()" in runner


def test_baseline_generator_is_scaffolded_and_store_scoped() -> None:
    generator = AlembicBaselineGenerator()
    specification = module_specification()
    path = PurePosixPath("migrations/identity/versions/0001_identity.py")
    files = generator.render(specification)

    assert set(files) == {path}
    ast.parse(files[path])
    assert "CREATE TABLE login_accounts" in files[path]
    assert "DROP TABLE IF EXISTS login_accounts CASCADE" in files[path]
    plan = generator.plan(specification)
    assert plan.files[0].ownership is FileOwnership.SCAFFOLDED


def test_mysql_baseline_uses_mysql_ddl_and_no_cascade_drop() -> None:
    specification = module_specification()
    assert specification.database is not None
    mysql_specification = specification.model_copy(
        update={"database": specification.database.model_copy(update={"provider": "mysql"})}
    )

    files = AlembicBaselineGenerator().render(mysql_specification)
    migration = files[PurePosixPath("migrations/identity/versions/0001_identity.py")]

    assert "CHAR(36) PRIMARY KEY" in migration
    assert "CASCADE" not in migration


def test_baseline_generator_renders_explicit_additive_revision() -> None:
    specification = module_specification()
    assert specification.database is not None
    login_table = specification.database.tables[0].model_copy(
        update={
            "columns": [
                *specification.database.tables[0].columns,
                ColumnSpec(
                    name="expires_at",
                    type=FieldType(kind=FieldTypeKind.DATETIME),
                    nullable=True,
                ),
            ]
        }
    )
    audit_table = TableSpec(
        name="audit_entries",
        columns=[
            ColumnSpec(
                name="audit_id",
                type=FieldType(kind=FieldTypeKind.UUID),
                primary_key=True,
            )
        ],
    )
    database = specification.database.model_copy(
        update={
            "tables": [login_table, audit_table],
            "placements": [
                *specification.database.placements,
                DataPlacementSpec(table="audit_entries", store="identity"),
            ],
            "migrations": [
                DatabaseMigrationSpec(
                    revision=2,
                    name="signal_delivery",
                    store="identity",
                    create_tables=["audit_entries"],
                    add_columns=[
                        AddColumnMigrationSpec(
                            table="login_accounts",
                            column=login_table.columns[-1],
                        )
                    ],
                )
            ],
        }
    )
    files = AlembicBaselineGenerator().render(
        specification.model_copy(update={"database": database})
    )

    baseline = files[PurePosixPath("migrations/identity/versions/0001_identity.py")]
    revision = files[
        PurePosixPath("migrations/identity/versions/0002_identity_signal_delivery.py")
    ]

    assert "expires_at" not in baseline
    assert "audit_entries" not in baseline
    assert "ALTER TABLE login_accounts ADD COLUMN expires_at" in revision
    assert "CREATE TABLE audit_entries" in revision
    assert "down_revision = 'af_identity_identity_0001'" in revision

    raw_files = PostgreSQLDDLGenerator().render(
        specification.model_copy(update={"database": database})
    )
    raw_baseline = raw_files[PurePosixPath("database/global/0001_identity.sql")]
    raw_revision = raw_files[
        PurePosixPath("database/global/0002_identity_signal_delivery.sql")
    ]
    assert "expires_at" not in raw_baseline
    assert "audit_entries" not in raw_baseline
    assert "ALTER TABLE login_accounts ADD COLUMN expires_at" in raw_revision
    assert "CREATE TABLE audit_entries" in raw_revision
