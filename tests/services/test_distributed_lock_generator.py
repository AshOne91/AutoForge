import ast
import os
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    DistributedLockSpec,
    ProjectInfo,
    ProjectSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.distributed_lock import DistributedLockGenerator
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator


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
    assert "REDIS_CLUSTER_STARTUP_NODES_ENV" in config
    assert "RedisCluster.from_url" in adapter


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
