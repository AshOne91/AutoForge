import ast
import os
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    KeyValueStoreSpec,
    ProjectInfo,
    ProjectSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.key_value_store import KeyValueStoreGenerator


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
            key_value_store=KeyValueStoreSpec(
                enabled=enabled,
                mode=mode,
                url_environment="KIS_CACHE_REDIS_URL",
                key_prefix="kis-cache",
                ttl_seconds=10,
            )
        ),
    )


def test_key_value_store_generator_is_empty_until_enabled() -> None:
    assert KeyValueStoreGenerator().render(specification()) == {}


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
