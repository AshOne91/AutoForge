from pathlib import PurePosixPath

from autoforge.core.generation import FileOwnership, Generator
from autoforge.services.generation import MySQLDDLGenerator, PostgreSQLDDLGenerator
from tests.services.test_postgresql_ddl_generator import database_specification


def mysql_specification():
    specification = database_specification()
    assert specification.database is not None
    return specification.model_copy(
        update={"database": specification.database.model_copy(update={"provider": "mysql"})}
    )


def test_mysql_ddl_generator_satisfies_protocol() -> None:
    generator: Generator = MySQLDDLGenerator()

    assert isinstance(generator, Generator)


def test_mysql_provider_renders_mysql_sql_only() -> None:
    rendered = MySQLDDLGenerator().render(mysql_specification())

    global_sql = rendered[PurePosixPath("database/global/0001_identity.sql")]
    assert "user_id CHAR(36) PRIMARY KEY" in global_sql
    assert "email VARCHAR(255) NOT NULL UNIQUE" in global_sql
    assert "TIMESTAMPTZ" not in global_sql
    assert PostgreSQLDDLGenerator().render(mysql_specification()) == {}


def test_mysql_plan_marks_sql_as_generated() -> None:
    plan = MySQLDDLGenerator().plan(mysql_specification())

    assert all(file.ownership is FileOwnership.GENERATED for file in plan.files)
