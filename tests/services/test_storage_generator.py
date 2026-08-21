import ast
import os
import socket
import sys
import uuid
from pathlib import Path, PurePosixPath

import anyio
import pytest
import yaml

from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
    StorageSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.storage import ObjectStorageGenerator


def specification(
    *,
    enabled: bool = True,
    runtime_enabled: bool = False,
    mode: str = "standalone",
    host_port_base: int = 49500,
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
            storage=StorageSpec(
                enabled=enabled,
                runtime_enabled=runtime_enabled,
                mode=mode,
                host_port_base=host_port_base,
            )
        ),
    )


def test_object_storage_generator_renders_minio_by_default() -> None:
    files = ObjectStorageGenerator().render(specification())

    assert PurePosixPath("deploy", "storage", "compose.storage.yaml") in files


def test_object_storage_generator_can_be_explicitly_disabled() -> None:
    assert ObjectStorageGenerator().render(specification(enabled=False)) == {}


def test_object_storage_generator_renders_default_minio_contract() -> None:
    files = ObjectStorageGenerator().render(specification())

    compose = files[PurePosixPath("deploy", "storage", "compose.storage.yaml")]
    environment = files[PurePosixPath("deploy", "storage", ".env.example")]
    readme = files[PurePosixPath("deploy", "storage", "README.md")]

    assert "minio/minio:RELEASE.2025-07-23T15-54-02Z" in compose
    assert "minio/mc:RELEASE.2025-08-13T08-35-41Z" in compose
    assert 'command: server /data --console-address ":9001"' in compose
    assert '"${LOCAL_BIND_ADDRESS:-127.0.0.1}:${MINIO_API_PORT:-49580}:9000"' in compose
    assert "S3_ENDPOINT_URL=http://minio:9000" in environment
    assert "S3_ACCESS_KEY=autoforge" in environment
    assert "S3_BUCKET=kis-auto-trading-artifacts" in environment
    assert "mc mb --ignore-existing" in compose
    assert "idempotently creates `S3_BUCKET`" in readme
    assert "rather than adding it to a Compose `--wait` health gate" in readme
    assert readme.endswith("file as a production topology.\n")
    parsed = yaml.safe_load(compose)
    assert set(parsed["services"]) == {"minio", "minio-init"}
    assert parsed["services"]["minio"]["profiles"] == ["storage"]
    assert parsed["services"]["minio"]["restart"] == "unless-stopped"
    assert parsed["services"]["minio-init"]["depends_on"]["minio"]["condition"] == "service_healthy"


def test_object_storage_generator_plan_marks_all_outputs_generated() -> None:
    plan = ObjectStorageGenerator().plan(specification())

    assert len(plan.files) == 3
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:object_storage"}


def test_object_storage_generator_renders_distributed_minio_behind_stable_endpoint() -> None:
    files = ObjectStorageGenerator().render(specification(mode="distributed"))
    compose = files[PurePosixPath("deploy", "storage", "compose.storage.yaml")]
    proxy = files[PurePosixPath("deploy", "storage", "nginx", "default.conf")]
    console = files[PurePosixPath("deploy", "storage", "nginx", "console.conf")]
    parsed = yaml.safe_load(compose)

    assert "S3_ENDPOINT_URL=http://minio:9000" in files[
        PurePosixPath("deploy", "storage", ".env.example")
    ]
    assert set(parsed["services"]) == {
        "minio",
        "minio-1",
        "minio-2",
        "minio-3",
        "minio-4",
        "minio-init",
        "minio-console",
    }
    assert all(
        parsed["services"][f"minio-{index}"]["command"]
        == "server http://minio-1/data http://minio-2/data http://minio-3/data http://minio-4/data --console-address \":9001\""
        for index in range(1, 5)
    )
    assert parsed["services"]["minio"]["depends_on"]["minio-4"] == {
        "condition": "service_healthy"
    }
    assert "proxy_next_upstream_tries 4" in proxy
    assert "proxy_next_upstream_tries 4" in console
    assert "four MinIO members" in files[PurePosixPath("deploy", "storage", "README.md")]
    assert set(parsed["volumes"]) == {
        "minio-1-data",
        "minio-2-data",
        "minio-3-data",
        "minio-4-data",
    }


@pytest.mark.integration
@pytest.mark.anyio
async def test_distributed_minio_reads_and_writes_after_member_stops(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_MINIO_DISTRIBUTED_INTEGRATION") != "1":
        pytest.skip("set AUTOFORGE_DOCKER_MINIO_DISTRIBUTED_INTEGRATION=1 to run Docker")

    host_port_base = next(
        base
        for base in range(49200, 65500, 100)
        if all(
            _port_is_available(port)
            for port in (base + 80, base + 81)
        )
    )
    package_name = f"storage_ha_{uuid.uuid4().hex}"
    specification_value = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Distributed Storage HA",
            package_name=package_name,
            version="0.1.0",
        ),
        application=ApplicationSpec(),
        tooling=ToolingSpec(
            storage=StorageSpec(mode="distributed", host_port_base=host_port_base)
        ),
    )
    files = ObjectStorageGenerator().render(specification_value)
    for relative_path, content in files.items():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    storage_dir = tmp_path / "deploy" / "storage"
    (storage_dir / ".env").write_text(
        files[PurePosixPath("deploy", "storage", ".env.example")], encoding="utf-8"
    )
    compose = (
        "docker",
        "compose",
        "--env-file",
        "deploy/storage/.env",
        "-f",
        "deploy/storage/compose.storage.yaml",
        "--profile",
        "storage",
    )
    runner = AsyncioProcessRunner()
    bucket = f"{package_name.replace('_', '-')}-artifacts"
    alias = (
        "exec",
        "-T",
        "minio-2",
        "mc",
        "alias",
        "set",
        "local",
        "http://minio:9000",
        "autoforge",
        "change-me",
    )
    try:
        result = await runner.run((*compose, "up", "--detach"), cwd=tmp_path, timeout_seconds=180)
        assert result.succeeded, result.stderr
        for _ in range(30):
            result = await runner.run((*compose, *alias), cwd=tmp_path, timeout_seconds=10)
            if result.succeeded:
                break
            await anyio.sleep(2)
        assert result.succeeded, result.stderr
        result = await runner.run(
            (*compose, "exec", "-T", "minio-2", "mc", "mb", "--ignore-existing", f"local/{bucket}"),
            cwd=tmp_path,
            timeout_seconds=20,
        )
        assert result.succeeded, result.stderr
        result = await runner.run(
            (
                *compose,
                "exec",
                "-T",
                "minio-2",
                "sh",
                "-ec",
                f"printf ha-check | mc pipe local/{bucket}/ha-check.txt && mc cat local/{bucket}/ha-check.txt",
            ),
            cwd=tmp_path,
            timeout_seconds=20,
        )
        assert result.succeeded, result.stderr
        assert result.stdout.strip().endswith("ha-check")
        result = await runner.run((*compose, "stop", "minio-1"), cwd=tmp_path, timeout_seconds=30)
        assert result.succeeded, result.stderr
        for _ in range(15):
            result = await runner.run(
                (
                    *compose,
                    "exec",
                    "-T",
                    "minio-2",
                    "sh",
                    "-ec",
                    f"printf ha-write | mc pipe local/{bucket}/ha-write-after-stop.txt",
                ),
                cwd=tmp_path,
                timeout_seconds=20,
            )
            if result.succeeded:
                break
            await anyio.sleep(2)
        assert result.succeeded, result.stderr
        result = await runner.run(
            (
                *compose,
                "exec",
                "-T",
                "minio-2",
                "mc",
                "cat",
                f"local/{bucket}/ha-write-after-stop.txt",
            ),
            cwd=tmp_path,
            timeout_seconds=20,
        )
        assert result.succeeded, result.stderr
        assert result.stdout.strip().endswith("ha-write")
        for _ in range(15):
            result = await runner.run(
                (*compose, "exec", "-T", "minio-2", "mc", "cat", f"local/{bucket}/ha-check.txt"),
                cwd=tmp_path,
                timeout_seconds=20,
            )
            if result.succeeded:
                break
            await anyio.sleep(2)
        assert result.succeeded, result.stderr
        assert result.stdout.strip().endswith("ha-check")
    finally:
        await runner.run(
            (*compose, "down", "--volumes", "--remove-orphans"),
            cwd=tmp_path,
            timeout_seconds=120,
        )


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def test_object_storage_runtime_is_opt_in_and_can_target_managed_storage() -> None:
    files = ObjectStorageGenerator().render(
        specification(enabled=False, runtime_enabled=True)
    )
    root = PurePosixPath("src", "kis_auto_trading", "infrastructure", "object_storage")

    assert set(files) == {
        root / "__init__.py",
        root / "config.py",
        root / "fake.py",
        root / "protocol.py",
        root / "s3.py",
        root / "service.py",
    }
    assert "class ObjectStorage:" in files[root / "service.py"]
    assert "class Aioboto3ObjectStorageClient:" in files[root / "s3.py"]
    assert "S3_ENDPOINT_URL" in files[root / "config.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_object_storage_runtime_adds_aioboto3_only_when_selected() -> None:
    runtime_files = FastAPIProjectGenerator().render(
        specification(runtime_enabled=True)
    )
    plain_files = FastAPIProjectGenerator().render(specification())
    runtime_dependencies, _ = runtime_files[PurePosixPath("pyproject.toml")].split(
        "[project.optional-dependencies]"
    )
    plain_dependencies, _ = plain_files[PurePosixPath("pyproject.toml")].split(
        "[project.optional-dependencies]"
    )

    assert '    "aioboto3>=15.5,<16",' in runtime_dependencies
    assert '    "aioboto3>=15.5,<16",' not in plain_dependencies


@pytest.mark.anyio
async def test_generated_object_storage_fake_is_deterministic(tmp_path: Path) -> None:
    specification_value = specification(runtime_enabled=True)
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    storage_generator = ObjectStorageGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("storage-job", storage_generator),
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
        "from kis_auto_trading.infrastructure.object_storage import (\n"
        "    FakeObjectStorageClient, ObjectStorage,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    storage = ObjectStorage(FakeObjectStorageClient())\n"
        "    await storage.health_check()\n"
        "    await storage.put_bytes('raw/b.txt', b'B')\n"
        "    await storage.put_bytes('raw/a.txt', b'A', content_type='text/plain')\n"
        "    assert await storage.get_bytes('raw/a.txt') == b'A'\n"
        "    assert await storage.list_keys('raw/') == ['raw/a.txt', 'raw/b.txt']\n"
        "    await storage.delete('raw/a.txt')\n"
        "    assert await storage.get_bytes('raw/a.txt') is None\n"
        "    await storage.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr


@pytest.mark.integration
@pytest.mark.anyio
async def test_generated_object_storage_adapter_runs_against_explicit_s3_endpoint(
    tmp_path: Path,
) -> None:
    endpoint = os.environ.get("AUTOFORGE_S3_INTEGRATION_ENDPOINT")
    if endpoint is None:
        pytest.skip("set AUTOFORGE_S3_INTEGRATION_ENDPOINT to run S3 integration")

    access_key = os.environ.get("AUTOFORGE_S3_INTEGRATION_ACCESS_KEY", "autoforge")
    secret_key = os.environ.get("AUTOFORGE_S3_INTEGRATION_SECRET_KEY", "change-me")
    bucket = os.environ.get("AUTOFORGE_S3_INTEGRATION_BUCKET", "autoforge-integration")
    specification_value = specification(runtime_enabled=True)
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    storage_generator = ObjectStorageGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("storage-job", storage_generator),
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
        "import aioboto3\n"
        "sys.path.insert(0, 'src')\n"
        "from kis_auto_trading.infrastructure.object_storage import ObjectStorage\n"
        f"ENDPOINT = {endpoint!r}\n"
        f"ACCESS_KEY = {access_key!r}\n"
        f"SECRET_KEY = {secret_key!r}\n"
        f"BUCKET = {bucket!r}\n"
        "\n"
        "async def verify():\n"
        "    session = aioboto3.Session()\n"
        "    async with session.client(\n"
        "        's3', endpoint_url=ENDPOINT, region_name='us-east-1',\n"
        "        aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY,\n"
        "    ) as bootstrap:\n"
        "        await bootstrap.create_bucket(Bucket=BUCKET)\n"
        "    os.environ.update({\n"
        "        'S3_ENDPOINT_URL': ENDPOINT, 'S3_BUCKET': BUCKET,\n"
        "        'S3_ACCESS_KEY': ACCESS_KEY, 'S3_SECRET_KEY': SECRET_KEY,\n"
        "        'S3_PREFIX': 'service',\n"
        "    })\n"
        "    storage = await ObjectStorage.from_environment()\n"
        "    try:\n"
        "        await storage.health_check()\n"
        "        await storage.put_bytes('raw/a.txt', b'A', content_type='text/plain')\n"
        "        assert await storage.get_bytes('raw/a.txt') == b'A'\n"
        "        assert await storage.list_keys('raw/') == ['raw/a.txt']\n"
        "        await storage.delete('raw/a.txt')\n"
        "        assert await storage.get_bytes('raw/a.txt') is None\n"
        "    finally:\n"
        "        await storage.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=30
    )

    assert result.succeeded, result.stderr
