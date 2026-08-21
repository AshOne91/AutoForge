import ast
import os
import sys
import uuid
from pathlib import Path, PurePosixPath

import anyio
import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    KeyValueStoreSpec,
    LocalEnvironmentSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.key_value_store import KeyValueStoreGenerator
from autoforge.services.generation.local_environment import LocalEnvironmentGenerator


def specification(
    *, enabled: bool = False, backend: str = "redis", mode: str = "standalone"
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
            key_value_store=KeyValueStoreSpec(
                enabled=enabled,
                backend=backend,
                mode=mode,
                url_environment="KIS_CACHE_REDIS_URL",
                key_prefix="kis-cache",
                ttl_seconds=10,
            )
        ),
    )


def test_key_value_store_generator_is_empty_until_enabled() -> None:
    assert KeyValueStoreGenerator().render(specification()) == {}


def test_key_value_store_rejects_memcached_redis_topology() -> None:
    with pytest.raises(
        ValueError, match="memcached key_value_store supports only standalone mode"
    ):
        KeyValueStoreSpec(enabled=True, backend="memcached", mode="cluster")


def test_key_value_store_generator_renders_generated_runtime_contract() -> None:
    files = KeyValueStoreGenerator().render(specification(enabled=True))
    root = PurePosixPath(
        "src", "kis_auto_trading", "infrastructure", "key_value_store"
    )

    assert set(files) == {
        root / "__init__.py",
        root / "config.py",
        root / "fake.py",
        root / "protocol.py",
        root / "redis.py",
        root / "service.py",
    }
    assert "KIS_CACHE_REDIS_URL" in files[root / "config.py"]
    assert 'DEFAULT_BACKEND: Final = "redis"' in files[root / "config.py"]
    assert 'DEFAULT_KEY_PREFIX: Final = "kis-cache"' in files[root / "config.py"]
    assert "mode: RedisMode = RedisMode.STANDALONE" in files[root / "config.py"]
    assert "class KeyValueStore:" in files[root / "service.py"]
    assert "class FakeKeyValueStoreClient:" in files[root / "fake.py"]
    assert "class RedisKeyValueStoreClient:" in files[root / "redis.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_key_value_store_generator_preserves_redis_cluster_selection() -> None:
    files = KeyValueStoreGenerator().render(
        specification(enabled=True, mode="cluster")
    )
    root = PurePosixPath(
        "src", "kis_auto_trading", "infrastructure", "key_value_store"
    )

    assert 'DEFAULT_MODE: Final = "cluster"' in files[root / "config.py"]
    assert "mode: RedisMode = RedisMode.CLUSTER" in files[root / "config.py"]
    assert "RedisCluster.from_url" in files[root / "redis.py"]


def test_key_value_store_generator_selects_memcached_adapter() -> None:
    files = KeyValueStoreGenerator().render(
        specification(enabled=True, backend="memcached")
    )
    root = PurePosixPath(
        "src", "kis_auto_trading", "infrastructure", "key_value_store"
    )

    assert root / "redis.py" not in files
    assert root / "memcached.py" in files
    assert 'DEFAULT_BACKEND: Final = "memcached"' in files[root / "config.py"]
    assert "MEMCACHED_HOST_ENV" in files[root / "config.py"]
    assert "class MemcachedKeyValueStoreClient:" in files[root / "memcached.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_key_value_store_plan_marks_runtime_contract_generated() -> None:
    plan = KeyValueStoreGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 6
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {
        "project:kis_auto_trading:key-value-store"
    }


def test_key_value_store_makes_redis_a_runtime_dependency() -> None:
    files = FastAPIProjectGenerator().render(specification(enabled=True))
    runtime_dependencies, _ = files[PurePosixPath("pyproject.toml")].split(
        "[project.optional-dependencies]"
    )

    assert '    "redis>=5,<7",' in runtime_dependencies


def test_key_value_store_makes_memcached_a_runtime_dependency() -> None:
    files = FastAPIProjectGenerator().render(
        specification(enabled=True, backend="memcached")
    )
    runtime_dependencies, _ = files[PurePosixPath("pyproject.toml")].split(
        "[project.optional-dependencies]"
    )

    assert '    "aiomcache>=0.8,<1",' in runtime_dependencies
    assert '    "redis>=5,<7",' not in runtime_dependencies


@pytest.mark.anyio
async def test_generated_key_value_store_fake_honors_ttl(tmp_path: Path) -> None:
    specification_value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    service_generator = KeyValueStoreGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("key-value-store-job", service_generator),
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
        "from kis_auto_trading.infrastructure.key_value_store import (\n"
        "    FakeKeyValueStoreClient, KeyValueStore,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    now = [0.0]\n"
        "    store = KeyValueStore(FakeKeyValueStoreClient(10, lambda: now[0]), 10)\n"
        "    await store.health_check()\n"
        "    await store.set('kis-token', 'cached-token')\n"
        "    assert await store.get('kis-token') == 'cached-token'\n"
        "    now[0] = 10.0\n"
        "    assert await store.get('kis-token') is None\n"
        "    await store.set('kis-token', 'cached-token')\n"
        "    assert await store.delete('kis-token')\n"
        "    assert not await store.delete('kis-token')\n"
        "    await store.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr


@pytest.mark.anyio
async def test_generated_memcached_adapter_uses_common_contract(tmp_path: Path) -> None:
    specification_value = specification(enabled=True, backend="memcached")
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    service_generator = KeyValueStoreGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("key-value-store-job", service_generator),
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
        "import types\n"
        "\n"
        "class Client:\n"
        "    def __init__(self, *args, **kwargs):\n"
        "        self.values = {}\n"
        "    async def version(self):\n"
        "        return b'1.0.0'\n"
        "    async def get(self, key):\n"
        "        return self.values.get(key)\n"
        "    async def set(self, key, value, *, exptime):\n"
        "        self.values[key] = value\n"
        "        return True\n"
        "    async def delete(self, key):\n"
        "        return self.values.pop(key, None) is not None\n"
        "    async def close(self):\n"
        "        return None\n"
        "\n"
        "sys.modules['aiomcache'] = types.SimpleNamespace(Client=Client)\n"
        "sys.path.insert(0, 'src')\n"
        "from kis_auto_trading.infrastructure.key_value_store import (\n"
        "    KeyValueStore, KeyValueStoreConfig, MemcachedKeyValueStoreClient,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    client = Client()\n"
        "    store = KeyValueStore(\n"
        "        MemcachedKeyValueStoreClient(KeyValueStoreConfig(), client=client), 10\n"
        "    )\n"
        "    await store.health_check()\n"
        "    await store.set('token', 'cached-token')\n"
        "    assert await store.get('token') == 'cached-token'\n"
        "    assert await store.delete('token')\n"
        "    assert await store.get('token') is None\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr


@pytest.mark.integration
@pytest.mark.anyio
async def test_generated_key_value_store_runs_against_explicit_redis(
    tmp_path: Path,
) -> None:
    redis_url = os.environ.get("AUTOFORGE_REDIS_KV_INTEGRATION_URL")
    if redis_url is None:
        pytest.skip("set AUTOFORGE_REDIS_KV_INTEGRATION_URL to run Redis integration")

    specification_value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    service_generator = KeyValueStoreGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("key-value-store-job", service_generator),
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
        "from kis_auto_trading.infrastructure.key_value_store import KeyValueStore\n"
        f"REDIS_URL = {redis_url!r}\n"
        "\n"
        "async def verify():\n"
        "    os.environ['KIS_CACHE_REDIS_URL'] = REDIS_URL\n"
        "    store = KeyValueStore.from_environment()\n"
        "    key = f'autoforge-integration:{uuid.uuid4().hex}'\n"
        "    try:\n"
        "        await store.health_check()\n"
        "        await store.set(key, 'cached-token', ttl_seconds=10)\n"
        "        assert await store.get(key) == 'cached-token'\n"
        "        assert await store.delete(key)\n"
        "        assert await store.get(key) is None\n"
        "    finally:\n"
        "        await store.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=20
    )

    assert result.succeeded, result.stderr


@pytest.mark.integration
@pytest.mark.anyio
async def test_generated_cluster_key_value_store_recovers_after_redis_primary_stops(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_REDIS_CLUSTER_KV_INTEGRATION") != "1":
        pytest.skip(
            "set AUTOFORGE_DOCKER_REDIS_CLUSTER_KV_INTEGRATION=1 to run Docker"
        )

    package_name = f"cache_ha_{uuid.uuid4().hex}"
    specification_value = specification(enabled=True, mode="cluster").model_copy(
        update={
            "project": ProjectInfo(
                name="Key Value Store HA",
                package_name=package_name,
                version="0.1.0",
            ),
            "application": ApplicationSpec(
                services=[
                    ServiceSpec(
                        name="session",
                        kind="redis_session",
                        namespace="cache",
                        ttl_seconds=60,
                        mode="cluster",
                    )
                ]
            ),
            "tooling": ToolingSpec(
                key_value_store=KeyValueStoreSpec(
                    enabled=True,
                    mode="cluster",
                    key_prefix="cache",
                    ttl_seconds=10,
                ),
                local_environment=LocalEnvironmentSpec(enabled=True),
            ),
        }
    )
    workspace = Workspace(tmp_path)
    generators = [
        ("project-job", FastAPIProjectGenerator()),
        ("key-value-store-job", KeyValueStoreGenerator()),
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
    script = workspace.root / "verify_store.py"
    script.write_text(
        "import asyncio\n"
        "import sys\n"
        "import uuid\n"
        "sys.path.insert(0, '/workspace/src')\n"
        f"from {package_name}.infrastructure.key_value_store import KeyValueStore\n"
        "\n"
        "async def verify():\n"
        "    store = KeyValueStore.from_environment()\n"
        "    try:\n"
        "        await store.health_check()\n"
        "        key = f'autoforge-cache:{uuid.uuid4().hex}'\n"
        "        await store.set(key, 'available', ttl_seconds=10)\n"
        "        assert await store.get(key) == 'available'\n"
        "        assert await store.delete(key)\n"
        "        assert await store.get(key) is None\n"
        "    finally:\n"
        "        await store.aclose()\n"
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

        result = await _run_cluster_store_probe(
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

        result = await _run_cluster_store_probe(
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
async def test_generated_sentinel_key_value_store_recovers_after_redis_primary_stops(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_REDIS_SENTINEL_KV_INTEGRATION") != "1":
        pytest.skip(
            "set AUTOFORGE_DOCKER_REDIS_SENTINEL_KV_INTEGRATION=1 to run Docker"
        )

    package_name = f"cache_sentinel_ha_{uuid.uuid4().hex}"
    sentinel_master = "cache-primary"
    specification_value = specification(enabled=True, mode="sentinel").model_copy(
        update={
            "project": ProjectInfo(
                name="Key Value Store Sentinel HA",
                package_name=package_name,
                version="0.1.0",
            ),
            "application": ApplicationSpec(
                services=[
                    ServiceSpec(
                        name="session",
                        kind="redis_session",
                        namespace="cache",
                        ttl_seconds=60,
                        mode="sentinel",
                        sentinel_master=sentinel_master,
                    )
                ]
            ),
            "tooling": ToolingSpec(
                key_value_store=KeyValueStoreSpec(
                    enabled=True,
                    mode="sentinel",
                    sentinel_master=sentinel_master,
                    key_prefix="cache",
                    ttl_seconds=10,
                ),
                local_environment=LocalEnvironmentSpec(enabled=True),
            ),
        }
    )
    workspace = Workspace(tmp_path)
    generators = [
        ("project-job", FastAPIProjectGenerator()),
        ("key-value-store-job", KeyValueStoreGenerator()),
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
    script = workspace.root / "verify_store.py"
    script.write_text(
        "import asyncio\n"
        "import sys\n"
        "import uuid\n"
        "sys.path.insert(0, '/workspace/src')\n"
        f"from {package_name}.infrastructure.key_value_store import KeyValueStore\n"
        "\n"
        "async def verify():\n"
        "    store = KeyValueStore.from_environment()\n"
        "    try:\n"
        "        await store.health_check()\n"
        "        key = f'autoforge-sentinel-cache:{uuid.uuid4().hex}'\n"
        "        await store.set(key, 'available', ttl_seconds=10)\n"
        "        assert await store.get(key) == 'available'\n"
        "        assert await store.delete(key)\n"
        "        assert await store.get(key) is None\n"
        "    finally:\n"
        "        await store.aclose()\n"
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
    sentinel_urls = (
        "redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379"
    )
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
                cwd=workspace.root,
                timeout_seconds=10,
            )
            if result.succeeded and result.stdout.startswith("OK"):
                break
            await anyio.sleep(2)
        assert result.succeeded and result.stdout.startswith("OK"), result.stderr

        master_before = await runner.run(
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
            cwd=workspace.root,
            timeout_seconds=10,
        )
        assert master_before.succeeded, master_before.stderr
        assert master_before.stdout.strip()

        result = await _run_sentinel_store_probe(
            runner, workspace.root, package_name, sentinel_urls
        )
        assert result.succeeded, result.stderr

        result = await runner.run(
            (*compose, "stop", "redis-sentinel-primary-1"),
            cwd=workspace.root,
            timeout_seconds=30,
        )
        assert result.succeeded, result.stderr
        master_after = master_before
        for _ in range(45):
            master_after = await runner.run(
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
                cwd=workspace.root,
                timeout_seconds=10,
            )
            if (
                master_after.succeeded
                and master_after.stdout.strip() != master_before.stdout.strip()
            ):
                break
            await anyio.sleep(2)
        assert master_after.succeeded, master_after.stderr
        assert master_after.stdout.strip() != master_before.stdout.strip()

        result = await _run_sentinel_store_probe(
            runner, workspace.root, package_name, sentinel_urls
        )
        assert result.succeeded, result.stderr
    finally:
        await runner.run(
            (*compose, "down", "--volumes", "--remove-orphans"),
            cwd=workspace.root,
            timeout_seconds=180,
        )


async def _run_cluster_store_probe(
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
            "pip install --disable-pip-version-check 'redis>=5,<7' && python verify_store.py",
        ),
        cwd=workspace_root,
        timeout_seconds=120,
    )


async def _run_sentinel_store_probe(
    runner: AsyncioProcessRunner,
    workspace_root: Path,
    package_name: str,
    sentinel_urls: str,
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
            f"REDIS_SENTINEL_URLS={sentinel_urls}",
            "python:3.12-alpine",
            "sh",
            "-c",
            "pip install --disable-pip-version-check 'redis>=5,<7' && python verify_store.py",
        ),
        cwd=workspace_root,
        timeout_seconds=120,
    )
