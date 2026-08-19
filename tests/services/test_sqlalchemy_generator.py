import ast
from pathlib import PurePosixPath

import pytest

from autoforge.core.generation import FileOwnership, Generator
from autoforge.core.specification import (
    ApplicationSpec,
    ColumnSpec,
    DatabaseShardSpec,
    DatabaseSpec,
    DatabaseStoreSpec,
    FieldType,
    FieldTypeKind,
    ModelSpec,
    ModuleInfo,
    ModuleSpec,
    ProjectInfo,
    ProjectSpec,
    RepositoryQuerySpec,
    RepositorySpec,
    TableSpec,
)
from autoforge.services.generation import (
    SQLAlchemyInfrastructureGenerator,
    SQLAlchemyModelGenerator,
)


def project_specification() -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(modules=["identity", "account"]),
    )


def module_specification() -> ModuleSpec:
    return ModuleSpec(
        spec_version="1",
        module=ModuleInfo(
            name="identity",
            display_name="Identity",
            route_prefix="/api/identity",
        ),
        models=[ModelSpec(name="LoginAccount")],
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
                )
            ],
            repositories=[
                RepositorySpec(
                    name="LoginAccountRepository",
                    aggregate="LoginAccount",
                    table="login_accounts",
                    operations=["find_by_id", "save"],
                )
            ],
        ),
    )


def test_sqlalchemy_generators_satisfy_protocol() -> None:
    project_generator: Generator[ProjectSpec] = (
        SQLAlchemyInfrastructureGenerator()
    )
    module_generator: Generator[ModuleSpec] = SQLAlchemyModelGenerator(
        "kis_auto_trading"
    )

    assert isinstance(project_generator, Generator)
    assert isinstance(module_generator, Generator)


def test_infrastructure_generator_renders_async_session_and_router() -> None:
    files = SQLAlchemyInfrastructureGenerator().render(project_specification())

    assert set(files) == {
        PurePosixPath("src/kis_auto_trading/infrastructure/__init__.py"),
        PurePosixPath(
            "src/kis_auto_trading/infrastructure/database/__init__.py"
        ),
        PurePosixPath("src/kis_auto_trading/infrastructure/database/base.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/database/routing.py"),
        PurePosixPath("src/kis_auto_trading/infrastructure/database/session.py"),
    }
    for content in files.values():
        ast.parse(content)

    routing = files[
        PurePosixPath("src/kis_auto_trading/infrastructure/database/routing.py")
    ]
    session = files[
        PurePosixPath("src/kis_auto_trading/infrastructure/database/session.py")
    ]
    assert "class ShardRouter(Protocol):" in routing
    assert "class ShardRoutingError(RuntimeError):" in routing
    assert "class AsyncSessionRegistry:" in session
    assert "async_sessionmaker(engine, expire_on_commit=False)" in session
    assert "async def health_check(self) -> None:" in session
    assert "await connection.execute(text('SELECT 1'))" in session
    assert "raise ShardRoutingError" in session
    assert "global" not in session.split("if engine is None:", maxsplit=1)[1]


def test_infrastructure_generator_renders_database_lifespan_provider() -> None:
    specification = project_specification().model_copy(
        update={
            "application": ApplicationSpec(
                modules=["identity", "account"],
                databases=[
                    DatabaseStoreSpec(
                        name="identity",
                        global_url_env="IDENTITY_DATABASE_URL",
                    ),
                    DatabaseStoreSpec(
                        name="profile",
                        shards=[
                            DatabaseShardSpec(
                                shard_id="1",
                                url_env="PROFILE_SHARD_1_DATABASE_URL",
                            )
                        ],
                    ),
                ],
            )
        }
    )
    files = SQLAlchemyInfrastructureGenerator().render(specification)
    provider_path = PurePosixPath(
        "src/kis_auto_trading/infrastructure/database/provider.py"
    )
    provider = files[provider_path]

    ast.parse(provider)
    assert "('identity', 'IDENTITY_DATABASE_URL')" in provider
    assert "('profile', '1', 'PROFILE_SHARD_1_DATABASE_URL')" in provider
    assert "GLOBAL_DATABASES = [('identity', 'IDENTITY_DATABASE_URL')]" in provider
    assert (
        "SHARD_DATABASES = [('profile', '1', 'PROFILE_SHARD_1_DATABASE_URL')]"
        in provider
    )
    assert "global_engines[store] = engine" in provider
    assert "shard_engines[(store, shard_id)] = engine" in provider
    assert "create_async_engine" in provider
    assert "app.state.session_registry" in provider
    assert "registry_registered = False" in provider
    assert "if registry_registered:" in provider
    assert "await engine.dispose()" in provider
    assert "def get_session_registry(request: Request)" in provider


def test_model_generator_renders_sqlalchemy_2_record() -> None:
    files = SQLAlchemyModelGenerator("kis_auto_trading").render(
        module_specification()
    )
    path = PurePosixPath(
        "src/kis_auto_trading/modules/identity/generated/sqlalchemy_models.py"
    )
    repository_path = path.with_name("sqlalchemy_repositories.py")
    assert set(files) == {path, repository_path}
    rendered = files[path]
    ast.parse(rendered)

    assert "class LoginAccountRecord(Base):" in rendered
    assert '__tablename__ = "login_accounts"' in rendered
    assert "user_id: Mapped[UUID]" in rendered
    assert "mapped_column(Uuid, primary_key=True)" in rendered
    assert "email: Mapped[str]" in rendered
    assert "unique=True" in rendered
    assert "index=True" in rendered
    assert "server_default=text('TRUE')" in rendered

    repository = files[repository_path]
    ast.parse(repository)
    assert "from uuid import UUID" in repository
    assert "class SQLAlchemyLoginAccountRepository:" in repository
    assert "def __init__(self, session: AsyncSession)" in repository
    assert "record = await self._session.get(" in repository
    assert "await self._session.merge(record)" in repository
    assert ".commit(" not in repository
    assert "return LoginAccount(" in repository
    assert "from sqlalchemy import select" not in repository


def test_model_generator_renders_unique_query() -> None:
    specification = module_specification()
    assert specification.database is not None
    specification.database.repositories[0].queries.append(
        RepositoryQuerySpec(name="find_by_email", column="email")
    )

    files = SQLAlchemyModelGenerator("kis_auto_trading").render(specification)
    repository = files[PurePosixPath(
        "src/kis_auto_trading/modules/identity/generated/"
        "sqlalchemy_repositories.py"
    )]

    ast.parse(repository)
    assert "async def find_by_email(" in repository
    assert "email: str" in repository
    assert "select(LoginAccountRecord).where(" in repository
    assert "LoginAccountRecord.email == email" in repository
    assert "result.scalar_one_or_none()" in repository


def test_sqlalchemy_plans_mark_files_generated() -> None:
    project_plan = SQLAlchemyInfrastructureGenerator().plan(
        project_specification()
    )
    module_plan = SQLAlchemyModelGenerator("kis_auto_trading").plan(
        module_specification()
    )

    assert project_plan.files
    assert module_plan.files
    assert all(
        file.ownership is FileOwnership.GENERATED
        for file in [*project_plan.files, *module_plan.files]
    )


def test_model_generator_requires_one_aggregate_per_table() -> None:
    specification = module_specification()
    assert specification.database is not None
    specification.database.repositories.clear()

    with pytest.raises(ValueError, match="exactly one aggregate"):
        SQLAlchemyModelGenerator("kis_auto_trading").render(specification)
