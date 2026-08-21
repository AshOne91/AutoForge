import ast
import os
import sys
import uuid
from pathlib import Path, PurePosixPath

import anyio
import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    DistributedLockSpec,
    LocalEnvironmentSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.distributed_lock import DistributedLockGenerator
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.local_environment import LocalEnvironmentGenerator


def specification(
    *, enabled: bool = False, mode: str = "standalone"
) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
        tooling=ToolingSpec(
            distributed_lock=DistributedLockSpec(
                enabled=enabled,
                mode=mode,
                url_environment="KIS_LOCK_REDIS_URL",
                key_prefix="kis-lock",
                ttl_seconds=10,
            )
        ),
    )


def test_distributed_lock_generator_is_empty_until_enabled() -> None:
    assert DistributedLockGenerator().render(specification()) == {}


def test_distributed_lock_generator_renders_generated_runtime_contract() -> None:
    files = DistributedLockGenerator().render(specification(enabled=True))
    root = PurePosixPath(
        "src", "kis_auto_trading", "infrastructure", "distributed_lock"
    )

    assert set(files) == {
        root / "__init__.py",
        root / "config.py",
        root / "fake.py",
        root / "protocol.py",
        root / "redis.py",
        root / "service.py",
    }
    assert "KIS_LOCK_REDIS_URL" in files[root / "config.py"]
    assert 'DEFAULT_KEY_PREFIX: Final = "kis-lock"' in files[root / "config.py"]
    assert "mode: RedisMode = RedisMode.STANDALONE" in files[root / "config.py"]
    assert "class DistributedLock:" in files[root / "service.py"]
    assert "class FakeDistributedLockClient:" in files[root / "fake.py"]
    assert "_RELEASE_IF_OWNER" in files[root / "redis.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_distributed_lock_generator_preserves_redis_cluster_selection() -> None:
    files = DistributedLockGenerator().render(
        specification(enabled=True, mode="cluster")
    )
    config = files[
        PurePosixPath(
            "src", "kis_auto_trading", "infrastructure", "distributed_lock", "config.py"
        )
    ]
    adapter = files[
        PurePosixPath(
            "src", "kis_auto_trading", "infrastructure", "distributed_lock", "redis.py"
        )
    ]

    assert 'DEFAULT_MODE: Final = "cluster"' in config
    assert "mode: RedisMode = RedisMode.CLUSTER" in config
    assert "REDIS_CLUSTER_STARTUP_NODES_ENV" in config
    assert "RedisCluster.from_url" in adapter


def test_distributed_lock_generator_preserves_redis_sentinel_selection() -> None:
    files = DistributedLockGenerator().render(
        specification(enabled=True, mode="sentinel")
    )
    root = PurePosixPath(
        "src", "kis_auto_trading", "infrastructure", "distributed_lock"
    )
    config = files[root / "config.py"]
    adapter = files[root / "redis.py"]

    assert 'DEFAULT_MODE: Final = "sentinel"' in config
    assert "mode: RedisMode = RedisMode.SENTINEL" in config
    assert "REDIS_SENTINEL_URLS_ENV" in config
    assert "Sentinel(" in adapter
    assert "self._sentinel.master_for(" in adapter


def test_distributed_lock_plan_marks_runtime_contract_generated() -> None:
    plan = DistributedLockGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 6
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {
        "project:kis_auto_trading:distributed-lock"
    }


def test_distributed_lock_makes_redis_a_runtime_dependency() -> None:
    files = FastAPIProjectGenerator().render(specification(enabled=True))
    runtime_dependencies, _ = files[PurePosixPath("pyproject.toml")].split(
        "[project.optional-dependencies]"
    )

    assert '    "redis>=5,<7",' in runtime_dependencies


@pytest.mark.anyio
async def test_generated_distributed_lock_fake_enforces_owner_and_ttl(
    tmp_path: Path,
) -> None:
    specification_value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    service_generator = DistributedLockGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("distributed-lock-job", service_generator),
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

    code = (
        "import asyncio\n"
        "import sys\n"
        "sys.path.insert(0, 'src')\n"
        "from kis_auto_trading.infrastructure.distributed_lock import (\n"
        "    DistributedLock, FakeDistributedLockClient,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    now = [0.0]\n"
        "    client = FakeDistributedLockClient(10, clock=lambda: now[0])\n"
        "    first = DistributedLock(client, 10)\n"
        "    second = DistributedLock(client, 10)\n"
        "    token = await first.acquire('token-refresh')\n"
        "    assert token == 'lock-token-1'\n"
        "    assert await second.acquire('token-refresh') is None\n"
        "    assert not await second.release('token-refresh', 'wrong-owner')\n"
        "    now[0] = 10.0\n"
        "    replacement = await second.acquire('token-refresh')\n"
        "    assert replacement == 'lock-token-2'\n"
        "    assert not await first.release('token-refresh', token)\n"
        "    assert await second.release('token-refresh', replacement)\n"
        "    await first.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr


@pytest.mark.integration
@pytest.mark.anyio
async def test_generated_distributed_lock_runs_against_explicit_redis(
    tmp_path: Path,
) -> None:
    redis_url = os.environ.get("AUTOFORGE_REDIS_LOCK_INTEGRATION_URL")
    if redis_url is None:
        pytest.skip("set AUTOFORGE_REDIS_LOCK_INTEGRATION_URL to run Redis integration")

    specification_value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    service_generator = DistributedLockGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("distributed-lock-job", service_generator),
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

    code = (
        "import asyncio\n"
        "import os\n"
        "import sys\n"
        "import uuid\n"
        "sys.path.insert(0, 'src')\n"
        "from kis_auto_trading.infrastructure.distributed_lock import DistributedLock\n"
        f"REDIS_URL = {redis_url!r}\n"
        "\n"
        "async def verify():\n"
        "    os.environ['KIS_LOCK_REDIS_URL'] = REDIS_URL\n"
        "    first = DistributedLock.from_environment()\n"
        "    second = DistributedLock.from_environment()\n"
        "    key = f'autoforge-integration:{uuid.uuid4().hex}'\n"
        "    try:\n"
        "        await first.health_check()\n"
        "        token = await first.acquire(key, ttl_seconds=2)\n"
        "        assert token is not None\n"
        "        assert await second.acquire(key) is None\n"
        "        assert not await second.release(key, 'wrong-owner')\n"
        "        assert await first.release(key, token)\n"
        "        replacement = await second.acquire(key)\n"
        "        assert replacement is not None\n"
        "        assert await second.release(key, replacement)\n"
        "    finally:\n"
        "        await first.aclose()\n"
        "        await second.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=20
    )

    assert result.succeeded, result.stderr


@pytest.mark.integration
@pytest.mark.anyio
async def test_generated_cluster_lock_recovers_after_redis_primary_stops(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_REDIS_CLUSTER_LOCK_INTEGRATION") != "1":
        pytest.skip(
            "set AUTOFORGE_DOCKER_REDIS_CLUSTER_LOCK_INTEGRATION=1 to run Docker"
        )

    package_name = f"lock_ha_{uuid.uuid4().hex}"
    specification_value = specification(enabled=True, mode="cluster").model_copy(
        update={
            "project": ProjectInfo(
                name="Distributed Lock HA",
                package_name=package_name,
                version="0.1.0",
            ),
            "application": ApplicationSpec(
                services=[
                    ServiceSpec(
                        name="session",
                        kind="redis_session",
                        namespace="lock",
                        ttl_seconds=60,
                        mode="cluster",
                    )
                ]
            ),
            "tooling": ToolingSpec(
                distributed_lock=DistributedLockSpec(
                    enabled=True,
                    mode="cluster",
                    key_prefix="lock",
                    ttl_seconds=10,
                ),
                local_environment=LocalEnvironmentSpec(enabled=True),
            ),
        }
    )
    workspace = Workspace(tmp_path)
    generators = [
        ("project-job", FastAPIProjectGenerator()),
        ("distributed-lock-job", DistributedLockGenerator()),
        ("environment-job", LocalEnvironmentGenerator()),
    ]
    for job_id, generator in generators:
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
    script = workspace.root / "verify_lock.py"
    script.write_text(
        "import asyncio\n"
        "import sys\n"
        "import uuid\n"
        "sys.path.insert(0, '/workspace/src')\n"
        f"from {package_name}.infrastructure.distributed_lock import DistributedLock\n"
        "\n"
        "async def verify():\n"
        "    lock = DistributedLock.from_environment()\n"
        "    try:\n"
        "        await lock.health_check()\n"
        "        key = f'autoforge-lock:{uuid.uuid4().hex}'\n"
        "        token = await lock.acquire(key)\n"
        "        assert token is not None\n"
        "        assert await lock.release(key, token)\n"
        "    finally:\n"
        "        await lock.aclose()\n"
        "\n"
        "asyncio.run(verify())\n",
        encoding="utf-8",
    )
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
    startup_nodes = ",".join(
        f"redis://redis-{port}:{port}" for port in range(7000, 7006)
    )
    runner = AsyncioProcessRunner()
    try:
        result = await runner.run(
            (*compose, "up", "--detach", "redis-cluster-init"),
            cwd=workspace.root,
            timeout_seconds=180,
        )
        assert result.succeeded, result.stderr
        for _ in range(45):
            result = await runner.run(
                (
                    *compose,
                    "exec",
                    "-T",
                    "redis-7001",
                    "redis-cli",
                    "-p",
                    "7001",
                    "cluster",
                    "info",
                ),
                cwd=workspace.root,
                timeout_seconds=10,
            )
            if "cluster_state:ok" in result.stdout:
                break
            await anyio.sleep(2)
        assert "cluster_state:ok" in result.stdout, result.stderr

        result = await _run_cluster_lock_probe(
            runner, workspace.root, package_name, startup_nodes
        )
        assert result.succeeded, result.stderr

        result = await runner.run(
            (*compose, "stop", "redis-7000"),
            cwd=workspace.root,
            timeout_seconds=30,
        )
        assert result.succeeded, result.stderr
        for _ in range(45):
            result = await runner.run(
                (
                    *compose,
                    "exec",
                    "-T",
                    "redis-7001",
                    "redis-cli",
                    "-p",
                    "7001",
                    "cluster",
                    "info",
                ),
                cwd=workspace.root,
                timeout_seconds=10,
            )
            if "cluster_state:ok" in result.stdout:
                break
            await anyio.sleep(2)
        assert "cluster_state:ok" in result.stdout, result.stderr

        result = await _run_cluster_lock_probe(
            runner, workspace.root, package_name, startup_nodes
        )
        assert result.succeeded, result.stderr
    finally:
        await runner.run(
            (*compose, "down", "--volumes", "--remove-orphans"),
            cwd=workspace.root,
            timeout_seconds=180,
        )


@pytest.mark.integration
@pytest.mark.anyio
async def test_generated_sentinel_lock_recovers_after_redis_primary_stops(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_REDIS_SENTINEL_LOCK_INTEGRATION") != "1":
        pytest.skip(
            "set AUTOFORGE_DOCKER_REDIS_SENTINEL_LOCK_INTEGRATION=1 to run Docker"
        )

    package_name = f"lock_sentinel_ha_{uuid.uuid4().hex}"
    sentinel_master = "lock-primary"
    specification_value = specification(enabled=True, mode="sentinel").model_copy(
        update={
            "project": ProjectInfo(
                name="Distributed Lock Sentinel HA",
                package_name=package_name,
                version="0.1.0",
            ),
            "application": ApplicationSpec(
                services=[
                    ServiceSpec(
                        name="session",
                        kind="redis_session",
                        namespace="lock",
                        ttl_seconds=60,
                        mode="sentinel",
                        sentinel_master=sentinel_master,
                    )
                ]
            ),
            "tooling": ToolingSpec(
                distributed_lock=DistributedLockSpec(
                    enabled=True,
                    mode="sentinel",
                    sentinel_master=sentinel_master,
                    key_prefix="lock",
                    ttl_seconds=10,
                ),
                local_environment=LocalEnvironmentSpec(enabled=True),
            ),
        }
    )
    workspace = Workspace(tmp_path)
    for job_id, generator in [
        ("project-job", FastAPIProjectGenerator()),
        ("distributed-lock-job", DistributedLockGenerator()),
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
    _write_sentinel_lock_probe(workspace.root, package_name)

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
                    "pip install --disable-pip-version-check 'redis>=5,<7' "
                    "&& python verify_sentinel_lock.py"
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


def _write_sentinel_lock_probe(workspace_root: Path, package_name: str) -> None:
    (workspace_root / "verify_sentinel_lock.py").write_text(
        "import asyncio\n"
        "import sys\n"
        "import uuid\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, '/workspace/src')\n"
        f"from {package_name}.infrastructure.distributed_lock import DistributedLock\n"
        "\n"
        "async def acquire_and_release(lock, key):\n"
        "    token = await lock.acquire(key)\n"
        "    assert token is not None\n"
        "    assert await lock.release(key, token)\n"
        "\n"
        "async def verify():\n"
        "    lock = DistributedLock.from_environment()\n"
        "    key = f'autoforge-sentinel-lock:{uuid.uuid4().hex}'\n"
        "    try:\n"
        "        await lock.health_check()\n"
        "        await acquire_and_release(lock, key)\n"
        "        print('BEFORE', flush=True)\n"
        "        for _ in range(900):\n"
        "            if Path('/workspace/continue').exists():\n"
        "                break\n"
        "            await asyncio.sleep(0.2)\n"
        "        else:\n"
        "            raise RuntimeError('test did not signal post-failover probe')\n"
        "        await acquire_and_release(lock, key)\n"
        "        print('AFTER', flush=True)\n"
        "    finally:\n"
        "        await lock.aclose()\n"
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


async def _run_cluster_lock_probe(
    runner: AsyncioProcessRunner,
    workspace_root: Path,
    package_name: str,
    startup_nodes: str,
) -> object:
    return await runner.run(
        (
            "docker",
            "run",
            "--rm",
            "--network",
            f"{package_name}_default",
            "--volume",
            f"{workspace_root.resolve()}:/workspace:ro",
            "--workdir",
            "/workspace",
            "--env",
            "REDIS_CLUSTER_URL=redis://redis-7000:7000",
            "--env",
            f"REDIS_CLUSTER_STARTUP_NODES={startup_nodes}",
            "python:3.12-alpine",
            "sh",
            "-c",
            "pip install --disable-pip-version-check 'redis>=5,<7' && python verify_lock.py",
        ),
        cwd=workspace_root,
        timeout_seconds=120,
    )
