import ast
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.generation import FileOwnership, Generator
from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import (
    FastAPIProjectGenerator,
    GenerationPlanApplier,
    GenerationPlanResolver,
    SessionStoreGenerator,
)


def project_specification(*, with_session: bool = True) -> ProjectSpec:
    services = []
    if with_session:
        services.append(
            ServiceSpec(
                name="session",
                kind="redis_session",
                namespace="kis_session",
                ttl_seconds=3600,
            )
        )
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(services=services),
    )


def sentinel_project_specification() -> ProjectSpec:
    specification = project_specification()
    service = specification.application.services[0].model_copy(
        update={
            "mode": "sentinel",
            "sentinel_urls_env": "KIS_REDIS_SENTINELS",
            "sentinel_master": "kis-session",
        }
    )
    return specification.model_copy(
        update={
            "application": specification.application.model_copy(
                update={"services": [service]}
            )
        }
    )


def test_session_store_generator_satisfies_protocol() -> None:
    generator: Generator[ProjectSpec] = SessionStoreGenerator()

    assert isinstance(generator, Generator)


def test_render_produces_protocol_fake_and_redis_adapter() -> None:
    files = SessionStoreGenerator().render(project_specification())
    root = PurePosixPath(
        "src/kis_auto_trading/infrastructure/session_store"
    )

    assert set(files) == {
        root / "__init__.py",
        root / "protocol.py",
        root / "fake.py",
        root / "provider.py",
        root / "redis.py",
    }
    for content in files.values():
        ast.parse(content)

    protocol = files[root / "protocol.py"]
    fake = files[root / "fake.py"]
    redis = files[root / "redis.py"]
    provider = files[root / "provider.py"]
    assert "class SessionStore(Protocol):" in protocol
    assert "async def revoke_user_sessions" in protocol
    assert "class FakeSessionStore:" in fake
    assert '_namespace = "kis_session"' in redis
    assert "_ttl_seconds = 3600" in redis
    assert "pipeline(transaction=True)" in redis
    assert "except RedisError as error:" in redis
    assert "SessionStoreError" in redis
    assert 'REDIS_URL_ENV = "REDIS_URL"' in provider
    assert "async def session_store_lifespan(" in provider
    assert "Redis.from_url(redis_url, decode_responses=True)" in provider
    assert "await client.aclose()" in provider
    assert "def get_session_store(request: Request)" in provider
    assert "bearer_scheme = HTTPBearer(auto_error=False)" in provider
    assert "async def get_current_session(" in provider
    assert "session_store.get(credentials.credentials)" in provider


def test_without_session_service_produces_no_files() -> None:
    generator = SessionStoreGenerator()
    specification = project_specification(with_session=False)

    assert generator.render(specification) == {}
    assert generator.plan(specification).files == []


def test_sentinel_provider_uses_declared_discovery_contract() -> None:
    files = SessionStoreGenerator().render(sentinel_project_specification())
    provider = files[PurePosixPath(
        "src/kis_auto_trading/infrastructure/session_store/provider.py"
    )]

    ast.parse(provider)
    assert 'REDIS_SENTINEL_URLS_ENV = "KIS_REDIS_SENTINELS"' in provider
    assert 'REDIS_SENTINEL_MASTER = "kis-session"' in provider
    assert "from redis.asyncio.sentinel import Sentinel" in provider
    assert "sentinel.master_for(" in provider
    assert "for sentinel_client in sentinel.sentinels:" in provider
    assert "async def get_current_session(" in provider


def test_plan_marks_all_session_files_generated() -> None:
    plan = SessionStoreGenerator().plan(project_specification())

    assert len(plan.files) == 5
    assert all(file.ownership is FileOwnership.GENERATED for file in plan.files)


def test_project_dependencies_include_redis_only_when_selected() -> None:
    generator = FastAPIProjectGenerator()

    with_redis = generator.render(project_specification())[
        PurePosixPath("pyproject.toml")
    ]
    without_redis = generator.render(
        project_specification(with_session=False)
    )[PurePosixPath("pyproject.toml")]

    assert '"redis>=5,<7"' in with_redis
    assert '"redis>=5,<7"' not in without_redis


@pytest.mark.anyio
async def test_generated_fake_honors_ttl_and_revocation(tmp_path: Path) -> None:
    specification = project_specification()
    generator = SessionStoreGenerator()
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    project_rendered = project_generator.render(specification)
    project_plan = GenerationPlanResolver().resolve(
        project_generator.plan(specification), workspace
    )
    GenerationPlanApplier().apply(
        job_id="project-job",
        plan=project_plan,
        rendered_files=project_rendered,
        workspace=workspace,
    )
    rendered = generator.render(specification)
    plan = GenerationPlanResolver().resolve(
        generator.plan(specification), workspace
    )
    GenerationPlanApplier().apply(
        job_id="session-store-job",
        plan=plan,
        rendered_files=rendered,
        workspace=workspace,
    )
    code = (
        "import asyncio\n"
        "import sys\n"
        "sys.path.insert(0, 'src')\n"
        "from kis_auto_trading.infrastructure.session_store import (\n"
        "    FakeSessionStore, SessionData,\n"
        ")\n"
        "now = [10.0]\n"
        "store = FakeSessionStore(5, clock=lambda: now[0])\n"
        "session = SessionData('s1', 'u1', {'role': 'user'})\n"
        "\n"
        "async def verify():\n"
        "    await store.create(session)\n"
        "    assert await store.get('s1') == session\n"
        "    assert await store.refresh('s1') is True\n"
        "    now[0] = 16.0\n"
        "    assert await store.get('s1') is None\n"
        "    await store.create(SessionData('s2', 'u1', {}))\n"
        "    await store.create(SessionData('s3', 'u1', {}))\n"
        "    assert await store.revoke_user_sessions('u1') == 2\n"
        "    assert await store.get('s2') is None\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code),
        cwd=workspace.root,
        timeout_seconds=10,
    )

    assert result.succeeded, result.stderr


@pytest.mark.anyio
async def test_generated_app_lifespan_initializes_and_closes_store(
    tmp_path: Path,
) -> None:
    specification = project_specification()
    workspace = Workspace(tmp_path)
    for job_id, generator in (
        ("project-job", FastAPIProjectGenerator()),
        ("session-store-job", SessionStoreGenerator()),
    ):
        rendered = generator.render(specification)
        plan = GenerationPlanResolver().resolve(
            generator.plan(specification), workspace
        )
        GenerationPlanApplier().apply(
            job_id=job_id,
            plan=plan,
            rendered_files=rendered,
            workspace=workspace,
        )

    code = (
        "import os\n"
        "import sys\n"
        "sys.path.insert(0, 'src')\n"
        "from fastapi.testclient import TestClient\n"
        "from kis_auto_trading.application.app_factory import create_app\n"
        "from kis_auto_trading.infrastructure.session_store import provider\n"
        "\n"
        "class FakeRedisClient:\n"
        "    def __init__(self):\n"
        "        self.closed = False\n"
        "    async def aclose(self):\n"
        "        self.closed = True\n"
        "\n"
        "client = FakeRedisClient()\n"
        "provider.Redis.from_url = lambda *args, **kwargs: client\n"
        "os.environ['REDIS_URL'] = 'redis://unused:6379/0'\n"
        "app = create_app()\n"
        "with TestClient(app):\n"
        "    assert app.state.session_store is not None\n"
        "assert client.closed is True\n"
        "assert not hasattr(app.state, 'session_store')\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code),
        cwd=workspace.root,
        timeout_seconds=10,
    )

    assert result.succeeded, result.stderr
