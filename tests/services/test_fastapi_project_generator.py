import ast
import importlib
import tomllib
from pathlib import Path, PurePosixPath

from autoforge.core.generation import (
    FileOwnership,
    Generator,
    content_hash,
)
from autoforge.core.specification import (
    ApplicationSpec,
    ControlPlaneHeartbeatSpec,
    DatabaseShardSpec,
    DatabaseStoreSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
    ServiceTokenSpec,
    ToolingSpec,
)
from autoforge.services.generation import FastAPIProjectGenerator


def project_specification(
    *,
    name: str = "Game Server",
    package_name: str = "game_server",
    description: str = "모듈형 FastAPI 게임 서버",
    modules: list[str] | None = None,
    services: list[ServiceSpec] | None = None,
    databases: list[DatabaseStoreSpec] | None = None,
    control_plane_heartbeat: ControlPlaneHeartbeatSpec | None = None,
    ruff_exclude: list[str] | None = None,
    dependencies: list[str] | None = None,
    database_provider: str = "postgresql",
    service_tokens: list[ServiceTokenSpec] | None = None,
) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name=name,
            package_name=package_name,
            version="0.1.0",
            description=description,
            dependencies=dependencies or [],
        ),
        application=ApplicationSpec(
            modules=modules or [],
            services=services or [],
            databases=databases or [],
            service_tokens=service_tokens or [],
            control_plane_heartbeat=control_plane_heartbeat
            or ControlPlaneHeartbeatSpec(),
        ),
        tooling=ToolingSpec(
            ruff_exclude=ruff_exclude or [],
            local_environment={"database_provider": database_provider},
        ),
    )


def test_fastapi_project_generator_satisfies_protocol() -> None:
    generator: Generator[ProjectSpec] = FastAPIProjectGenerator()

    assert isinstance(generator, Generator)


def test_render_returns_minimum_fastapi_project_files() -> None:
    files = FastAPIProjectGenerator().render(project_specification())

    assert set(files) == {
        PurePosixPath(".gitignore"),
        PurePosixPath("pyproject.toml"),
        PurePosixPath("README.md"),
        PurePosixPath("src/game_server/__init__.py"),
        PurePosixPath("src/game_server/main.py"),
        PurePosixPath("src/game_server/modules/__init__.py"),
        PurePosixPath("src/game_server/application/__init__.py"),
        PurePosixPath("src/game_server/application/observability.py"),
        PurePosixPath("src/game_server/application/extensions.py"),
        PurePosixPath("src/game_server/application/app_factory.py"),
        PurePosixPath("src/game_server/application/generated/__init__.py"),
        PurePosixPath("src/game_server/application/generated/lifespan.py"),
        PurePosixPath("src/game_server/application/generated/module_registry.py"),
        PurePosixPath("src/game_server/routers/__init__.py"),
        PurePosixPath("src/game_server/routers/health.py"),
        PurePosixPath("tests/test_health.py"),
    }


def test_render_uses_project_information() -> None:
    files = FastAPIProjectGenerator().render(
        project_specification(name="Tutorial Server")
    )

    assert (
        'title="Tutorial Server"'
        in files[PurePosixPath("src/game_server/application/app_factory.py")]
    )
    assert (
        "from game_server.application"
        in files[PurePosixPath("src/game_server/main.py")]
    )
    assert 'pip install -e ".[test]"' in files[PurePosixPath("README.md")]
    assert "uvicorn game_server.main:app" in files[PurePosixPath("README.md")]


def test_render_gitignore_covers_validation_build_artifacts() -> None:
    files = FastAPIProjectGenerator().render(project_specification())

    gitignore = files[PurePosixPath(".gitignore")].splitlines()

    assert "build/" in gitignore
    assert "dist/" in gitignore
    assert ".autoforge/dist/" in gitignore
    assert "logs/" in gitignore


def test_render_pyproject_includes_declared_ruff_exclusions() -> None:
    files = FastAPIProjectGenerator().render(
        project_specification(ruff_exclude=["reference", "manual_probe.py"])
    )

    pyproject = tomllib.loads(files[PurePosixPath("pyproject.toml")])

    assert pyproject["project"]["optional-dependencies"]["test"] == [
        "httpx",
        "pytest",
        "ruff",
    ]
    assert pyproject["tool"]["ruff"]["extend-exclude"] == [
        "reference",
        "manual_probe.py",
    ]


def test_render_pyproject_includes_declared_project_dependencies() -> None:
    files = FastAPIProjectGenerator().render(
        project_specification(dependencies=["yfinance>=0.2,<1"])
    )

    pyproject = tomllib.loads(files[PurePosixPath("pyproject.toml")])

    assert pyproject["project"]["dependencies"][-1] == "yfinance>=0.2,<1"


def test_render_empty_module_registry() -> None:
    files = FastAPIProjectGenerator().render(project_specification())
    registry = files[
        PurePosixPath("src/game_server/application/generated/module_registry.py")
    ]

    assert "MODULE_ROUTERS: tuple[APIRouter, ...] = ()" in registry


def test_render_module_registry_in_declared_order() -> None:
    files = FastAPIProjectGenerator().render(
        project_specification(modules=["tutorial", "item"])
    )
    registry = files[
        PurePosixPath("src/game_server/application/generated/module_registry.py")
    ]

    router_tuple = registry.split("MODULE_ROUTERS", maxsplit=1)[1]
    assert router_tuple.index("tutorial_router") < router_tuple.index("item_router")
    assert "    tutorial_router,\n    item_router,\n" in registry


def test_render_module_registry_wraps_long_imports_for_ruff() -> None:
    files = FastAPIProjectGenerator().render(
        project_specification(
            package_name="kis_auto_trading",
            modules=["market_data"],
        )
    )
    registry = files[
        PurePosixPath("src/kis_auto_trading/application/generated/module_registry.py")
    ]

    assert "from kis_auto_trading.modules.market_data.generated.router import (" in registry
    assert "    router as market_data_router,\n)" in registry
    assert all(len(line) <= 88 for line in registry.splitlines())


def test_app_factory_registers_module_routers() -> None:
    files = FastAPIProjectGenerator().render(project_specification())
    app_factory = files[PurePosixPath("src/game_server/application/app_factory.py")]
    extensions = files[PurePosixPath("src/game_server/application/extensions.py")]

    assert "import USER_ROUTERS" in app_factory
    assert "for router in USER_ROUTERS:" in app_factory
    assert "import MODULE_ROUTERS" in app_factory
    assert "for router in MODULE_ROUTERS:" in app_factory
    assert "app.include_router(router)" in app_factory
    assert "configure_logging()" in app_factory
    assert "install_request_logging(app)" in app_factory
    assert "USER_ROUTERS: tuple[APIRouter, ...] = ()" in extensions
    assert "USER_LIFESPANS: tuple[UserLifespanFactory, ...] = ()" in extensions


def test_lifespan_supports_user_contexts_and_legacy_extensions(
    tmp_path: Path, monkeypatch
) -> None:
    package_name = "lifecycle_server"
    files = dict(
        FastAPIProjectGenerator().render(project_specification(package_name=package_name))
    )
    extensions_path = PurePosixPath(
        f"src/{package_name}/application/extensions.py"
    )
    files[extensions_path] = (
        "from fastapi import APIRouter\n\n"
        "USER_ROUTERS: tuple[APIRouter, ...] = ()\n"
    )
    lifespan = files[
        PurePosixPath(f"src/{package_name}/application/generated/lifespan.py")
    ]

    assert "getattr(extensions, 'USER_LIFESPANS', ())" in lifespan
    for relative_path, content in files.items():
        target = tmp_path.joinpath(*relative_path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path / "src"))
    app = importlib.import_module(f"{package_name}.main").app

    assert app.title == "Game Server"


def test_observability_records_safe_request_metadata() -> None:
    files = FastAPIProjectGenerator().render(project_specification())
    observability = files[
        PurePosixPath("src/game_server/application/observability.py")
    ]

    assert "LOG_DIRECTORY" in observability
    assert "X-Request-ID" in observability
    assert "request.url.path" in observability
    assert "request.url.query" not in observability
    assert "RotatingFileHandler" in observability
    assert "'event_type', 'job_type', 'job_id'" in observability
    assert "'run_key', 'attempt', 'max_attempts'" in observability


def test_session_service_generates_and_registers_lifespan() -> None:
    service = ServiceSpec(
        name="session",
        kind="redis_session",
        namespace="game_session",
        ttl_seconds=3600,
        url_env="GAME_REDIS_URL",
    )
    files = FastAPIProjectGenerator().render(
        project_specification(services=[service])
    )
    lifespan_path = PurePosixPath(
        "src/game_server/application/generated/lifespan.py"
    )
    app_factory = files[
        PurePosixPath("src/game_server/application/app_factory.py")
    ]
    health_test = files[PurePosixPath("tests/test_health.py")]

    assert lifespan_path in files
    assert "AsyncExitStack" in files[lifespan_path]
    assert "session_store_lifespan(app)" in files[lifespan_path]
    assert files[lifespan_path].index("session_store_lifespan(app)") < files[
        lifespan_path
    ].index("for lifespan_factory in getattr(extensions, 'USER_LIFESPANS', ())")
    assert "application starting" in files[lifespan_path]
    assert "application stopping" in files[lifespan_path]
    assert "from game_server.application.generated.lifespan import lifespan" in (
        app_factory
    )
    assert "lifespan=lifespan" in app_factory
    assert 'monkeypatch.setenv("GAME_REDIS_URL"' in health_test
    health_router = files[PurePosixPath("src/game_server/routers/health.py")]
    assert '@router.get("/health")' in health_router
    assert '@router.get("/readiness")' in health_router
    assert "detail=f'{state_name} is not ready'" in health_router
    assert "except (SessionStoreError):" in health_router
    assert "assert not_ready.status_code == 503" in health_test
    assert 'readiness.json() == {"status": "ready"}' in health_test


def test_control_plane_heartbeat_generates_opt_in_lifecycle_reporter() -> None:
    files = FastAPIProjectGenerator().render(
        project_specification(
            databases=[DatabaseStoreSpec(name="identity", global_url_env="IDENTITY_URL")],
            services=[
                ServiceSpec(
                    name="session",
                    kind="redis_session",
                    namespace="game_session",
                    ttl_seconds=3600,
                )
            ],
            control_plane_heartbeat=ControlPlaneHeartbeatSpec(enabled=True),
        )
    )
    reporter = files[
        PurePosixPath("src/game_server/application/generated/service_heartbeat.py")
    ]
    lifespan = files[
        PurePosixPath("src/game_server/application/generated/lifespan.py")
    ]

    ast.parse(reporter)
    assert lifespan.index("from game_server.application import extensions") < lifespan.index(
        "application.generated.service_heartbeat"
    )
    assert lifespan.index("application.generated.service_heartbeat") < lifespan.index(
        "application.observability"
    )
    assert "service_heartbeat_lifespan(app)" in lifespan
    assert lifespan.index("database_lifespan(app)") < lifespan.index(
        "service_heartbeat_lifespan(app)"
    )
    assert lifespan.index("session_store_lifespan(app)") < lifespan.index(
        "service_heartbeat_lifespan(app)"
    )
    assert "CONTROL_PLANE_HEARTBEAT_URL" in reporter
    assert "CONTROL_PLANE_API_TOKEN" in reporter
    assert "async def run_service_heartbeat_reporter(" in reporter
    assert "run_service_heartbeat_reporter()" in reporter
    assert "_post_heartbeat, endpoint, token, service_name, dependencies" in reporter
    assert "except (OSError, ValueError) as error" in reporter
    assert "'dependencies': dependencies" in reporter


def test_cluster_session_service_generates_cluster_health_environment() -> None:
    service = ServiceSpec(
        name="session",
        kind="redis_session",
        namespace="game_session",
        ttl_seconds=3600,
        mode="cluster",
        cluster_url_env="GAME_REDIS_CLUSTER_URL",
    )

    files = FastAPIProjectGenerator().render(
        project_specification(services=[service])
    )
    health_test = files[PurePosixPath("tests/test_health.py")]

    assert 'monkeypatch.setenv("GAME_REDIS_CLUSTER_URL"' in health_test
    assert "redis://localhost:16379" in health_test


def test_rabbitmq_service_adds_aio_pika_dependency() -> None:
    service = ServiceSpec(
        name="events",
        kind="rabbitmq",
        outbox_stores=["account"],
    )
    database = DatabaseStoreSpec(
        name="account",
        shards=[DatabaseShardSpec(shard_id="1", url_env="ACCOUNT_URL")],
    )

    files = FastAPIProjectGenerator().render(
        project_specification(services=[service], databases=[database])
    )

    assert '"aio-pika>=9.5,<10"' in files[PurePosixPath("pyproject.toml")]


def test_database_store_generates_and_registers_lifespan() -> None:
    database = DatabaseStoreSpec(
        name="identity",
        global_url_env="IDENTITY_DATABASE_URL",
        shards=[
            DatabaseShardSpec(
                shard_id="1",
                url_env="IDENTITY_SHARD_1_DATABASE_URL",
            )
        ],
    )
    files = FastAPIProjectGenerator().render(
        project_specification(databases=[database])
    )
    lifespan = files[
        PurePosixPath("src/game_server/application/generated/lifespan.py")
    ]
    health_test = files[PurePosixPath("tests/test_health.py")]
    health_router = files[PurePosixPath("src/game_server/routers/health.py")]

    assert "database_lifespan(app)" in lifespan
    assert "session_store_lifespan" not in lifespan
    assert 'monkeypatch.setenv("IDENTITY_DATABASE_URL"' in health_test
    assert 'monkeypatch.setenv("IDENTITY_SHARD_1_DATABASE_URL"' in health_test
    assert "postgresql+asyncpg://" in health_test
    assert "except (SQLAlchemyError, OSError):" in health_router


def test_render_composes_identity_session_and_sharded_profile_foundation() -> None:
    session = ServiceSpec(
        name="session",
        kind="redis_session",
        namespace="game_session",
        ttl_seconds=3600,
        mode="cluster",
        cluster_url_env="GAME_REDIS_CLUSTER_URL",
    )
    identity = DatabaseStoreSpec(
        name="identity",
        global_url_env="IDENTITY_DATABASE_URL",
    )
    account = DatabaseStoreSpec(
        name="account",
        shards=[
            DatabaseShardSpec(
                shard_id="1",
                url_env="ACCOUNT_SHARD_1_DATABASE_URL",
            ),
            DatabaseShardSpec(
                shard_id="2",
                url_env="ACCOUNT_SHARD_2_DATABASE_URL",
            ),
        ],
    )

    files = FastAPIProjectGenerator().render(
        project_specification(
            modules=["identity", "account"],
            services=[session],
            databases=[identity, account],
        )
    )

    module_registry = files[
        PurePosixPath("src/game_server/application/generated/module_registry.py")
    ]
    lifespan = files[
        PurePosixPath("src/game_server/application/generated/lifespan.py")
    ]
    health_test = files[PurePosixPath("tests/test_health.py")]

    assert "game_server.modules.identity.generated.router" in module_registry
    assert "game_server.modules.account.generated.router" in module_registry
    assert "    identity_router," in module_registry
    assert "    account_router," in module_registry
    assert "database_lifespan(app)" in lifespan
    assert "session_store_lifespan(app)" in lifespan
    assert 'monkeypatch.setenv("GAME_REDIS_CLUSTER_URL"' in health_test
    assert 'monkeypatch.setenv("IDENTITY_DATABASE_URL"' in health_test
    assert 'monkeypatch.setenv("ACCOUNT_SHARD_1_DATABASE_URL"' in health_test
    assert 'monkeypatch.setenv("ACCOUNT_SHARD_2_DATABASE_URL"' in health_test


def test_rendered_python_and_toml_are_valid() -> None:
    files = FastAPIProjectGenerator().render(project_specification())

    for path, content in files.items():
        if path.suffix == ".py":
            ast.parse(content)

    pyproject = tomllib.loads(files[PurePosixPath("pyproject.toml")])
    assert pyproject["project"]["name"] == "game_server"
    assert pyproject["project"]["requires-python"] == ">=3.12"
    assert "sqlalchemy>=2.0,<3" in pyproject["project"]["dependencies"]
    assert "asyncpg>=0.30,<1" in pyproject["project"]["dependencies"]
    assert "alembic>=1.18,<2" in pyproject["project"]["dependencies"]
    assert pyproject["project"]["optional-dependencies"]["test"] == [
        "httpx",
        "pytest",
        "ruff",
    ]
    assert pyproject["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]
    assert pyproject["tool"]["ruff"]["lint"]["isort"]["known-first-party"] == [
        "game_server"
    ]


def test_mysql_runtime_selects_async_driver_and_health_url() -> None:
    database = DatabaseStoreSpec(
        name="identity",
        global_url_env="IDENTITY_DATABASE_URL",
    )
    files = FastAPIProjectGenerator().render(
        project_specification(databases=[database], database_provider="mysql")
    )

    pyproject = tomllib.loads(files[PurePosixPath("pyproject.toml")])
    health_test = files[PurePosixPath("tests/test_health.py")]

    assert "asyncmy>=0.2,<1" in pyproject["project"]["dependencies"]
    assert "cryptography>=44,<47" in pyproject["project"]["dependencies"]
    assert "asyncpg>=0.30,<1" not in pyproject["project"]["dependencies"]
    assert "mysql+asyncmy://" in health_test


def test_service_tokens_generate_a_shared_scope_guard() -> None:
    files = FastAPIProjectGenerator().render(
        project_specification(
            service_tokens=[
                ServiceTokenSpec(name="operator", token_env="OPERATOR_API_TOKEN")
            ]
        )
    )

    guard = files[
        PurePosixPath("src/game_server/infrastructure/service_tokens.py")
    ]

    ast.parse(guard)
    assert "'operator': 'OPERATOR_API_TOKEN'" in guard
    assert "compare_digest(token, expected_token)" in guard
    assert "service API token is not configured" in guard


def test_plan_matches_rendered_content_hashes() -> None:
    generator = FastAPIProjectGenerator()
    specification = project_specification()
    rendered_files = generator.render(specification)

    plan = generator.plan(specification)

    assert len(plan.files) == len(rendered_files)
    for planned_file in plan.files:
        content = rendered_files[planned_file.relative_path]
        assert planned_file.expected_content_hash == content_hash(content)


def test_user_maintained_project_files_are_scaffolded() -> None:
    plan = FastAPIProjectGenerator().plan(project_specification())
    ownership = {file.relative_path: file.ownership for file in plan.files}

    assert ownership[PurePosixPath("README.md")] is FileOwnership.SCAFFOLDED
    assert ownership[PurePosixPath(".gitignore")] is FileOwnership.SCAFFOLDED
    extension_path = PurePosixPath("src/game_server/application/extensions.py")
    assert ownership[extension_path] is FileOwnership.SCAFFOLDED
    assert all(
        value is FileOwnership.GENERATED
        for path, value in ownership.items()
        if path
        not in {
            PurePosixPath(".gitignore"),
            PurePosixPath("README.md"),
            extension_path,
        }
    )


def test_same_specification_produces_same_render_and_plan() -> None:
    generator = FastAPIProjectGenerator()
    specification = project_specification()

    assert generator.render(specification) == generator.render(specification)
    assert generator.plan(specification) == generator.plan(specification)


def test_project_name_changes_related_content_hash() -> None:
    generator = FastAPIProjectGenerator()
    first_plan = generator.plan(project_specification(name="First Server"))
    second_plan = generator.plan(project_specification(name="Second Server"))
    app_factory_path = PurePosixPath("src/game_server/application/app_factory.py")

    first_file = next(
        file for file in first_plan.files if file.relative_path == app_factory_path
    )
    second_file = next(
        file for file in second_plan.files if file.relative_path == app_factory_path
    )

    assert first_file.expected_content_hash != second_file.expected_content_hash


def test_render_and_plan_do_not_write_files(tmp_path) -> None:
    before = set(tmp_path.rglob("*"))
    generator = FastAPIProjectGenerator()

    generator.render(project_specification())
    generator.plan(project_specification())

    assert set(tmp_path.rglob("*")) == before
