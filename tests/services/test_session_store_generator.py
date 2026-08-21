import ast
import os
import sys
import uuid
from pathlib import Path, PurePosixPath

import anyio
import pytest

from autoforge.core.generation import FileOwnership, Generator
from autoforge.core.specification import (
    ApplicationSpec,
    LocalEnvironmentSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import (
    FastAPIProjectGenerator,
    GenerationPlanApplier,
    GenerationPlanResolver,
    LocalEnvironmentGenerator,
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


def cluster_project_specification() -> ProjectSpec:
    specification = project_specification()
    service = specification.application.services[0].model_copy(
        update={
            "mode": "cluster",
            "cluster_url_env": "KIS_REDIS_CLUSTER_URL",
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
        root.parent / "access_control.py",
        root / "__init__.py",
        root / "protocol.py",
        root / "fake.py",
        root / "provider.py",
        root / "redis.py",
        root / "request_replay.py",
    }
    for content in files.values():
        ast.parse(content)

    protocol = files[root / "protocol.py"]
    fake = files[root / "fake.py"]
    redis = files[root / "redis.py"]
    replay = files[root / "request_replay.py"]
    provider = files[root / "provider.py"]
    access_control = files[root.parent / "access_control.py"]
    assert "class SessionStore(Protocol):" in protocol
    assert "def create_session_id(user_id: str) -> str:" in protocol
    assert "def _session_routing_tag(session_id: str) -> str:" in protocol
    assert "async def revoke_user_sessions" in protocol
    assert "async def health_check(self) -> None:" in protocol
    assert "class FakeSessionStore:" in fake
    assert '_namespace = "kis_session"' in redis
    assert "_ttl_seconds = 3600" in redis
    assert "pipeline(transaction=True)" in redis
    assert "if not await self._client.ping():" in redis
    assert "except RedisError as error:" in redis
    assert "SessionStoreError" in redis
    assert "Redis | RedisCluster" in redis
    assert 'f"{self._namespace}:{{{routing_tag}}}:session:' in redis
    assert "class RedisRequestReplayStore:" in replay
    assert "_COMPLETE_SCRIPT" in replay
    assert 'REDIS_URL_ENV = "REDIS_URL"' in provider
    assert "async def session_store_lifespan(" in provider
    assert "Redis.from_url(redis_url, decode_responses=True)" in provider
    assert "await client.aclose()" in provider
    assert "def get_session_store(request: Request)" in provider
    assert "bearer_scheme = HTTPBearer(auto_error=False)" in provider
    assert "async def get_current_session(" in provider
    assert "session_store.get(credentials.credentials)" in provider
    assert "class AccessLevel(StrEnum):" in access_control
    assert "def require_access_level(required: AccessLevel)" in access_control
    assert "session access level is invalid" in access_control


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


def test_cluster_provider_uses_async_cluster_discovery_contract() -> None:
    files = SessionStoreGenerator().render(cluster_project_specification())
    provider = files[
        PurePosixPath(
            "src/kis_auto_trading/infrastructure/session_store/provider.py"
        )
    ]

    ast.parse(provider)
    assert 'REDIS_CLUSTER_URL_ENV = "KIS_REDIS_CLUSTER_URL"' in provider
    assert 'REDIS_CLUSTER_STARTUP_NODES_ENV = "REDIS_CLUSTER_STARTUP_NODES"' in provider
    assert "def _cluster_startup_nodes() -> list[ClusterNode]:" in provider
    assert "startup_nodes=_cluster_startup_nodes() or None" in provider
    assert "from redis.cluster import ClusterNode" in provider
    assert "from redis.asyncio.cluster import RedisCluster" in provider
    assert "RedisCluster.from_url(" in provider
    assert "require_full_coverage=True" in provider
    assert "await client.initialize()" not in provider
    assert "await client.aclose()" in provider


def test_plan_marks_all_session_files_generated() -> None:
    plan = SessionStoreGenerator().plan(project_specification())

    assert len(plan.files) == 7
    assert all(file.ownership is FileOwnership.GENERATED for file in plan.files)


def test_same_session_specification_is_reproducible() -> None:
    generator = SessionStoreGenerator()
    specification = project_specification()

    assert generator.render(specification) == generator.render(specification)
    assert generator.plan(specification) == generator.plan(specification)


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


@pytest.mark.integration
@pytest.mark.anyio
async def test_generated_sentinel_session_store_recovers_after_redis_primary_stops(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_REDIS_SENTINEL_SESSION_INTEGRATION") != "1":
        pytest.skip(
            "set AUTOFORGE_DOCKER_REDIS_SENTINEL_SESSION_INTEGRATION=1 to run Docker"
        )

    package_name = f"session_sentinel_ha_{uuid.uuid4().hex}"
    sentinel_master = "session-primary"
    specification_value = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Session Store Sentinel HA",
            package_name=package_name,
            version="0.1.0",
        ),
        application=ApplicationSpec(
            services=[
                ServiceSpec(
                    name="session",
                    kind="redis_session",
                    namespace="session",
                    ttl_seconds=3600,
                    mode="sentinel",
                    sentinel_master=sentinel_master,
                )
            ]
        ),
        tooling=ToolingSpec(local_environment=LocalEnvironmentSpec(enabled=True)),
    )
    workspace = Workspace(tmp_path)
    for job_id, generator in [
        ("project-job", FastAPIProjectGenerator()),
        ("session-store-job", SessionStoreGenerator()),
        ("environment-job", LocalEnvironmentGenerator()),
    ]:
        rendered = generator.render(specification_value)
        plan = GenerationPlanResolver().resolve(
            generator.plan(specification_value), workspace
        )
        GenerationPlanApplier().apply(
            job_id=job_id,
            plan=plan,
            rendered_files=rendered,
            workspace=workspace,
        )

    environment_dir = workspace.root / "environment"
    (environment_dir / ".env").write_text(
        (environment_dir / ".env.example").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _write_sentinel_session_probe(workspace.root, package_name)

    compose = (
        "docker",
        "compose",
        "--project-name",
        package_name,
        "--env-file",
        "environment/.env",
        "-f",
        "environment/compose.integration.yml",
    )
    sentinel_urls = (
        "redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379"
    )
    probe_name = f"{package_name}-probe"
    runner = AsyncioProcessRunner()
    try:
        result = await runner.run(
            (
                *compose,
                "up",
                "--detach",
                "redis-sentinel-1",
                "redis-sentinel-2",
                "redis-sentinel-3",
            ),
            cwd=workspace.root,
            timeout_seconds=180,
        )
        assert result.succeeded, result.stderr
        await _wait_for_sentinel_quorum(
            runner, workspace.root, compose, sentinel_master
        )
        master_before = await _sentinel_master_address(
            runner, workspace.root, compose, sentinel_master
        )

        result = await runner.run(
            (
                "docker",
                "run",
                "--detach",
                "--name",
                probe_name,
                "--network",
                f"{package_name}_default",
                "--volume",
                f"{workspace.root.resolve()}:/workspace",
                "--workdir",
                "/workspace",
                "--env",
                f"REDIS_SENTINEL_URLS={sentinel_urls}",
                "python:3.12-alpine",
                "sh",
                "-c",
                (
                    "pip install --disable-pip-version-check 'fastapi>=0.110,<1' "
                    "'redis>=5,<7' && python verify_sentinel_session.py"
                ),
            ),
            cwd=workspace.root,
            timeout_seconds=120,
        )
        assert result.succeeded, result.stderr
        await _wait_for_docker_log(runner, workspace.root, probe_name, "BEFORE")

        result = await runner.run(
            (*compose, "stop", "redis-sentinel-primary-1"),
            cwd=workspace.root,
            timeout_seconds=30,
        )
        assert result.succeeded, result.stderr
        master_after = master_before
        for _ in range(45):
            master_after = await _sentinel_master_address(
                runner, workspace.root, compose, sentinel_master
            )
            if master_after != master_before:
                break
            await anyio.sleep(2)
        assert master_after != master_before

        await anyio.sleep(15)
        (workspace.root / "continue").write_text("continue\n", encoding="utf-8")
        await _wait_for_docker_log(runner, workspace.root, probe_name, "AFTER")
        result = await runner.run(
            ("docker", "wait", probe_name),
            cwd=workspace.root,
            timeout_seconds=120,
        )
        assert result.succeeded, result.stderr
        assert result.stdout.strip() == "0"
    finally:
        await runner.run(
            ("docker", "rm", "--force", probe_name),
            cwd=workspace.root,
            timeout_seconds=30,
        )
        await runner.run(
            (*compose, "down", "--volumes", "--remove-orphans"),
            cwd=workspace.root,
            timeout_seconds=180,
        )


def _write_sentinel_session_probe(workspace_root: Path, package_name: str) -> None:
    (workspace_root / "verify_sentinel_session.py").write_text(
        "import asyncio\n"
        "import sys\n"
        "from pathlib import Path\n"
        "from fastapi import FastAPI\n"
        "sys.path.insert(0, '/workspace/src')\n"
        f"from {package_name}.infrastructure.session_store import (\n"
        "    SessionData,\n"
        "    create_session_id,\n"
        ")\n"
        f"from {package_name}.infrastructure.session_store.provider import (\n"
        "    session_store_lifespan,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    app = FastAPI()\n"
        "    async with session_store_lifespan(app):\n"
        "        store = app.state.session_store\n"
        "        session = SessionData(\n"
        "            create_session_id('user-1'), 'user-1', {'role': 'user'}\n"
        "        )\n"
        "        await store.create(session)\n"
        "        assert await store.get(session.session_id) == session\n"
        "        print('BEFORE', flush=True)\n"
        "        for _ in range(900):\n"
        "            if Path('/workspace/continue').exists():\n"
        "                break\n"
        "            await asyncio.sleep(0.2)\n"
        "        else:\n"
        "            raise RuntimeError('test did not signal post-failover probe')\n"
        "        assert await store.get(session.session_id) == session\n"
        "        print('AFTER', flush=True)\n"
        "\n"
        "asyncio.run(verify())\n",
        encoding="utf-8",
    )


async def _wait_for_sentinel_quorum(
    runner: AsyncioProcessRunner,
    workspace_root: Path,
    compose: tuple[str, ...],
    sentinel_master: str,
) -> None:
    result = None
    for _ in range(45):
        result = await runner.run(
            (
                *compose,
                "exec",
                "-T",
                "redis-sentinel-1",
                "redis-cli",
                "-p",
                "26379",
                "sentinel",
                "ckquorum",
                sentinel_master,
            ),
            cwd=workspace_root,
            timeout_seconds=10,
        )
        if result.succeeded and result.stdout.startswith("OK"):
            return
        await anyio.sleep(2)
    assert result is not None
    pytest.fail(result.stderr or result.stdout)


async def _sentinel_master_address(
    runner: AsyncioProcessRunner,
    workspace_root: Path,
    compose: tuple[str, ...],
    sentinel_master: str,
) -> str:
    result = await runner.run(
        (
            *compose,
            "exec",
            "-T",
            "redis-sentinel-1",
            "redis-cli",
            "--raw",
            "-p",
            "26379",
            "sentinel",
            "get-master-addr-by-name",
            sentinel_master,
        ),
        cwd=workspace_root,
        timeout_seconds=10,
    )
    assert result.succeeded, result.stderr
    assert result.stdout.strip()
    return result.stdout.strip()


async def _wait_for_docker_log(
    runner: AsyncioProcessRunner,
    workspace_root: Path,
    container_name: str,
    expected: str,
) -> None:
    result = None
    for _ in range(60):
        result = await runner.run(
            ("docker", "logs", container_name),
            cwd=workspace_root,
            timeout_seconds=10,
        )
        if result.succeeded and expected in result.stdout + result.stderr:
            return
        await anyio.sleep(1)
    assert result is not None
    pytest.fail(result.stdout + result.stderr)


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
