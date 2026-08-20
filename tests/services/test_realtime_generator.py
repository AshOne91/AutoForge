import ast
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
    RealtimeSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.realtime import RealtimeGenerator


def specification(*, enabled: bool = False) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
        tooling=ToolingSpec(realtime=RealtimeSpec(enabled=enabled)),
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
    }
    assert "class RealtimeSubscriber(Protocol):" in files[root / "protocol.py"]
    assert "class FakeRealtimeSubscriber:" in files[root / "fake.py"]
    assert "class RealtimeHub:" in files[root / "service.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_realtime_plan_marks_runtime_contract_generated() -> None:
    plan = RealtimeGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 4
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:kis_auto_trading:realtime"}


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
        "    FakeRealtimeSubscriber, RealtimeHub,\n"
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
