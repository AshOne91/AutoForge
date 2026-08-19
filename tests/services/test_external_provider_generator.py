import ast
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    ExternalProviderSpec,
    ProjectInfo,
    ProjectSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.external_provider import ExternalProviderGenerator
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator


def specification(*, enabled: bool = False) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
        tooling=ToolingSpec(
            external_provider=ExternalProviderSpec(
                enabled=enabled,
                url_environment="MARKET_DATA_URL",
                health_path="/healthz",
                max_retries=1,
                retry_delay_seconds=0,
            )
        ),
    )


def test_external_provider_generator_is_empty_until_enabled() -> None:
    assert ExternalProviderGenerator().render(specification()) == {}


def test_external_provider_generator_renders_generated_runtime_contract() -> None:
    files = ExternalProviderGenerator().render(specification(enabled=True))
    root = PurePosixPath(
        "src", "kis_auto_trading", "infrastructure", "external_provider"
    )

    assert set(files) == {
        root / "__init__.py",
        root / "config.py",
        root / "fake.py",
        root / "http_client.py",
        root / "protocol.py",
        root / "service.py",
    }
    assert "MARKET_DATA_URL" in files[root / "config.py"]
    assert "DEFAULT_HEALTH_PATH: Final = \"/healthz\"" in files[root / "config.py"]
    assert "class ExternalProvider:" in files[root / "service.py"]
    assert "class FakeExternalProviderClient:" in files[root / "fake.py"]
    assert "class ExternalResponse:" in files[root / "protocol.py"]
    assert "retry_safe" in files[root / "http_client.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_external_provider_plan_marks_runtime_contract_generated() -> None:
    plan = ExternalProviderGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 6
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {
        "project:kis_auto_trading:external-provider"
    }


def test_external_provider_makes_httpx_a_runtime_dependency() -> None:
    files = FastAPIProjectGenerator().render(specification(enabled=True))
    runtime_dependencies, _ = files[PurePosixPath("pyproject.toml")].split(
        "[project.optional-dependencies]"
    )

    assert '    "httpx>=0.28,<1",' in runtime_dependencies


@pytest.mark.anyio
async def test_generated_external_provider_fake_is_deterministic(tmp_path: Path) -> None:
    specification_value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    service_generator = ExternalProviderGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("external-provider-job", service_generator),
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
        "from kis_auto_trading.infrastructure.external_provider import (\n"
        "    ExternalProvider, ExternalResponse, FakeExternalProviderClient,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    client = FakeExternalProviderClient([\n"
        "        ExternalResponse(202, {'x-provider': 'fake'}, b'accepted')\n"
        "    ])\n"
        "    provider = ExternalProvider(client)\n"
        "    await provider.health_check()\n"
        "    response = await provider.request('POST', '/jobs', json={'name': 'sync'})\n"
        "    assert response.status_code == 202\n"
        "    assert response.content == b'accepted'\n"
        "    assert client.requests == [('POST', '/jobs')]\n"
        "    await provider.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr


@pytest.mark.anyio
async def test_generated_external_provider_retries_only_safe_requests(
    tmp_path: Path,
) -> None:
    specification_value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    service_generator = ExternalProviderGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("external-provider-job", service_generator),
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
        "import httpx\n"
        "sys.path.insert(0, 'src')\n"
        "from kis_auto_trading.infrastructure.external_provider import (\n"
        "    ExternalProviderConfig, HttpExternalProviderClient,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    get_calls = []\n"
        "    async def get_handler(request):\n"
        "        get_calls.append(request)\n"
        "        return httpx.Response(503 if len(get_calls) == 1 else 200, request=request)\n"
        "    get_client = httpx.AsyncClient(\n"
        "        transport=httpx.MockTransport(get_handler), base_url='https://provider.test'\n"
        "    )\n"
        "    config = ExternalProviderConfig(\n"
        "        'https://provider.test', max_retries=1, retry_delay_seconds=0\n"
        "    )\n"
        "    get_provider = HttpExternalProviderClient(config, client=get_client)\n"
        "    assert (await get_provider.request('GET', '/prices')).status_code == 200\n"
        "    assert len(get_calls) == 2\n"
        "    await get_provider.aclose()\n"
        "    assert not get_client.is_closed\n"
        "    await get_client.aclose()\n"
        "\n"
        "    post_calls = []\n"
        "    async def post_handler(request):\n"
        "        post_calls.append(request)\n"
        "        return httpx.Response(503, request=request)\n"
        "    post_client = httpx.AsyncClient(\n"
        "        transport=httpx.MockTransport(post_handler), base_url='https://provider.test'\n"
        "    )\n"
        "    post_provider = HttpExternalProviderClient(config, client=post_client)\n"
        "    assert (await post_provider.request('POST', '/orders')).status_code == 503\n"
        "    assert len(post_calls) == 1\n"
        "    await post_client.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr
