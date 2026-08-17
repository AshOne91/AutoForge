import ast
from pathlib import PurePosixPath

from autoforge.core.generation import FileOwnership
from autoforge.core.specification import ModuleSpec, ProjectSpec
from autoforge.services.generation.alembic import (
    AlembicBaselineGenerator,
    AlembicEnvironmentGenerator,
)


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
