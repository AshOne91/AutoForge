import ast
import os
import sys
import uuid
from pathlib import Path, PurePosixPath

import anyio
import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    LocalEnvironmentSpec,
    ProjectInfo,
    ProjectSpec,
    RealtimeSpec,
    ServiceSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.local_environment import LocalEnvironmentGenerator
from autoforge.services.generation.realtime import RealtimeGenerator


def specification(
    *,
    enabled: bool = False,
    backplane: str = "none",
    redis_mode: str = "standalone",
) -> ProjectSpec:
    services = []
    if backplane == "redis_pubsub":
        services.append(
            ServiceSpec(
                name="session",
                kind="redis_session",
                namespace="realtime",
                ttl_seconds=3600,
                mode=redis_mode,
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
        tooling=ToolingSpec(
            realtime=RealtimeSpec(enabled=enabled, backplane=backplane)
        ),
    )


def test_realtime_generator_is_empty_until_enabled() -> None:
    assert RealtimeGenerator().render(specification()) == {}


def test_realtime_generator_renders_generated_runtime_contract() -> None:
    files = RealtimeGenerator().render(specification(enabled=True))
    root = PurePosixPath("src", "kis_auto_trading", "infrastructure", "realtime")

    assert set(files) == {
        root / "__init__.py",
        root / "fake.py",
        root / "protocol.py",
        root / "service.py",
        root / "websocket.py",
    }
    assert "class RealtimeSubscriber(Protocol):" in files[root / "protocol.py"]
    assert "class FakeRealtimeSubscriber:" in files[root / "fake.py"]
    assert "class RealtimeHub:" in files[root / "service.py"]
    assert "class FastAPIWebSocketSubscriber:" in files[root / "websocket.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_realtime_plan_marks_runtime_contract_generated() -> None:
    plan = RealtimeGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 5
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:kis_auto_trading:realtime"}


def test_realtime_generator_renders_opt_in_redis_backplane() -> None:
    files = RealtimeGenerator().render(
        specification(enabled=True, backplane="redis_pubsub", redis_mode="cluster")
    )
    root = PurePosixPath("src", "kis_auto_trading", "infrastructure", "realtime")

    assert root / "backplane.py" in files
    assert "class RedisPubSubRealtimeBackplane:" in files[root / "backplane.py"]
    assert "REDIS_CLUSTER_STARTUP_NODES_ENV" in files[root / "backplane.py"]
    assert "class FakeRealtimeBackplane:" in files[root / "fake.py"]
    assert "class RealtimeBackplane(Protocol):" in files[root / "protocol.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_realtime_generator_renders_sentinel_backplane() -> None:
    files = RealtimeGenerator().render(
        specification(enabled=True, backplane="redis_pubsub", redis_mode="sentinel")
    )
    root = PurePosixPath("src", "kis_auto_trading", "infrastructure", "realtime")
    backplane = files[root / "backplane.py"]

    assert "from redis.asyncio.sentinel import Sentinel" in backplane
    assert "REDIS_SENTINEL_URLS_ENV" in backplane
    assert "REDIS_SENTINEL_MASTER" in backplane
    assert "sentinel_master=_redis_sentinel_master_from_environment()" in backplane
    assert "self._sentinel.master_for(" in backplane
    ast.parse(backplane, filename=(root / "backplane.py").as_posix())


@pytest.mark.anyio
async def test_generated_realtime_hub_fans_out_without_transport_policy(
    tmp_path: Path,
) -> None:
    specification_value = specification(enabled=True)
    workspace = Workspace(tmp_path)

    for job_id, generator in [
        ("project-job", FastAPIProjectGenerator()),
        ("realtime-job", RealtimeGenerator()),
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
        "from kis_auto_trading.infrastructure.realtime import (\n"
        "    FakeRealtimeSubscriber, FastAPIWebSocketSubscriber, RealtimeHub,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    hub = RealtimeHub()\n"
        "    first = FakeRealtimeSubscriber()\n"
        "    second = FakeRealtimeSubscriber()\n"
        "    await hub.subscribe('prices', first)\n"
        "    await hub.subscribe('prices', first)\n"
        "    await hub.subscribe('prices', second)\n"
        "    assert await hub.publish('prices', '{\"symbol\": \"005930\"}') == 2\n"
        "    assert first.messages == ['{\"symbol\": \"005930\"}']\n"
        "    assert second.messages == ['{\"symbol\": \"005930\"}']\n"
        "    await hub.unsubscribe('prices', second)\n"
        "    assert await hub.publish('prices', 'closed') == 1\n"
        "    class Socket:\n"
        "        def __init__(self): self.messages = []\n"
        "        async def send_text(self, message): self.messages.append(message)\n"
        "    socket = Socket()\n"
        "    websocket_subscriber = FastAPIWebSocketSubscriber(socket)\n"
        "    await hub.subscribe('prices', websocket_subscriber)\n"
        "    assert await hub.publish('prices', 'websocket') == 2\n"
        "    assert socket.messages == ['websocket']\n"
        "    await hub.aclose()\n"
        "    try:\n"
        "        await hub.publish('prices', 'ignored')\n"
        "    except RuntimeError:\n"
        "        pass\n"
        "    else:\n"
        "        raise AssertionError('closed hub accepted publish')\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr

@pytest.mark.anyio
async def test_generated_realtime_backplane_fake_delivers_hints(
    tmp_path: Path,
) -> None:
    specification_value = specification(enabled=True, backplane="redis_pubsub")
    workspace = Workspace(tmp_path)

    for job_id, generator in [
        ("project-job", FastAPIProjectGenerator()),
        ("realtime-job", RealtimeGenerator()),
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
        "from kis_auto_trading.infrastructure.realtime import FakeRealtimeBackplane\n"
        "\n"
        "async def verify():\n"
        "    delivered = []\n"
        "    async def deliver(channel, message):\n"
        "        delivered.append((channel, message))\n"
        "    backplane = FakeRealtimeBackplane()\n"
        "    await backplane.start(deliver)\n"
        "    await backplane.publish('user:1', '{\"notification_id\": \"n1\"}')\n"
        "    assert backplane.published == [('user:1', '{\"notification_id\": \"n1\"}')]\n"
        "    assert delivered == [('user:1', '{\"notification_id\": \"n1\"}')]\n"
        "    await backplane.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr

    ruff_result = await AsyncioProcessRunner().run(
        (sys.executable, "-m", "ruff", "check", "--no-cache", "src"),
        cwd=workspace.root,
        timeout_seconds=10,
    )

    assert ruff_result.succeeded, ruff_result.stderr


@pytest.mark.integration
@pytest.mark.anyio
async def test_generated_sentinel_realtime_backplane_recovers_after_redis_primary_stops(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_REDIS_SENTINEL_REALTIME_INTEGRATION") != "1":
        pytest.skip(
            "set AUTOFORGE_DOCKER_REDIS_SENTINEL_REALTIME_INTEGRATION=1 to run Docker"
        )

    package_name = f"realtime_sentinel_ha_{uuid.uuid4().hex}"
    sentinel_master = "session-primary"
    specification_value = specification(
        enabled=True, backplane="redis_pubsub", redis_mode="sentinel"
    ).model_copy(
        update={
            "project": ProjectInfo(
                name="Realtime Sentinel HA",
                package_name=package_name,
                version="0.1.0",
            ),
            "tooling": ToolingSpec(
                realtime=RealtimeSpec(enabled=True, backplane="redis_pubsub"),
                local_environment=LocalEnvironmentSpec(enabled=True),
            ),
        }
    )
    workspace = Workspace(tmp_path)
    for job_id, generator in [
        ("project-job", FastAPIProjectGenerator()),
        ("realtime-job", RealtimeGenerator()),
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
    _write_sentinel_realtime_scripts(workspace.root, package_name)

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
    listener_name = f"{package_name}-listener"
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
                listener_name,
                "--network",
                f"{package_name}_default",
                "--volume",
                f"{workspace.root.resolve()}:/workspace:ro",
                "--workdir",
                "/workspace",
                "--env",
                f"REDIS_SENTINEL_URLS={sentinel_urls}",
                "python:3.12-alpine",
                "sh",
                "-c",
                (
                    "pip install --disable-pip-version-check 'fastapi>=0.110,<1' "
                    "'redis>=5,<7' "
                    "&& python verify_realtime_listener.py"
                ),
            ),
            cwd=workspace.root,
            timeout_seconds=120,
        )
        assert result.succeeded, result.stderr
        await _wait_for_docker_log(runner, workspace.root, listener_name, "READY")

        result = await _run_sentinel_realtime_publisher(
            runner, workspace.root, package_name, sentinel_urls, "before"
        )
        assert result.succeeded, result.stderr
        await _wait_for_docker_log(
            runner, workspace.root, listener_name, "DELIVERED:before"
        )

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
        result = await _run_sentinel_realtime_publisher(
            runner, workspace.root, package_name, sentinel_urls, "after"
        )
        assert result.succeeded, result.stderr
        await _wait_for_docker_log(
            runner, workspace.root, listener_name, "DELIVERED:after"
        )

        result = await runner.run(
            ("docker", "wait", listener_name),
            cwd=workspace.root,
            timeout_seconds=120,
        )
        assert result.succeeded, result.stderr
        assert result.stdout.strip() == "0"
    finally:
        await runner.run(
            ("docker", "rm", "--force", listener_name),
            cwd=workspace.root,
            timeout_seconds=30,
        )
        await runner.run(
            (*compose, "down", "--volumes", "--remove-orphans"),
            cwd=workspace.root,
            timeout_seconds=180,
        )


def _write_sentinel_realtime_scripts(workspace_root: Path, package_name: str) -> None:
    (workspace_root / "verify_realtime_listener.py").write_text(
        "import asyncio\n"
        "import sys\n"
        "sys.path.insert(0, '/workspace/src')\n"
        f"from {package_name}.infrastructure.realtime import RedisPubSubRealtimeBackplane\n"
        "\n"
        "async def verify():\n"
        "    delivered_after = asyncio.Event()\n"
        "    async def deliver(channel, message):\n"
        "        print(f'DELIVERED:{message}', flush=True)\n"
        "        if message == 'after':\n"
        "            delivered_after.set()\n"
        "    backplane = RedisPubSubRealtimeBackplane.from_environment()\n"
        "    try:\n"
        "        await backplane.start(deliver)\n"
        "        print('READY', flush=True)\n"
        "        await asyncio.wait_for(delivered_after.wait(), timeout=180)\n"
        "    finally:\n"
        "        await backplane.aclose()\n"
        "\n"
        "asyncio.run(verify())\n",
        encoding="utf-8",
    )
    (workspace_root / "publish_realtime.py").write_text(
        "import asyncio\n"
        "import sys\n"
        "sys.path.insert(0, '/workspace/src')\n"
        f"from {package_name}.infrastructure.realtime import RedisPubSubRealtimeBackplane\n"
        "\n"
        "async def publish():\n"
        "    backplane = RedisPubSubRealtimeBackplane.from_environment()\n"
        "    try:\n"
        "        await backplane.publish('user:1', sys.argv[1])\n"
        "    finally:\n"
        "        await backplane.aclose()\n"
        "\n"
        "asyncio.run(publish())\n",
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
    for _ in range(45):
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


async def _run_sentinel_realtime_publisher(
    runner: AsyncioProcessRunner,
    workspace_root: Path,
    package_name: str,
    sentinel_urls: str,
    message: str,
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
            (
                "pip install --disable-pip-version-check 'fastapi>=0.110,<1' "
                "'redis>=5,<7' "
                f"&& python publish_realtime.py {message}"
            ),
        ),
        cwd=workspace_root,
        timeout_seconds=120,
    )
