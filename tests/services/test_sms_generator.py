import ast
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
    SmsSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.sms import SmsGenerator


def specification(*, enabled: bool = False) -> ProjectSpec:
    return ProjectSpec(spec_version="1", project=ProjectInfo(name="KIS", package_name="kis_auto_trading", version="0.1.0"), application=ApplicationSpec(), tooling=ToolingSpec(sms=SmsSpec(enabled=enabled)))


def test_sms_generator_is_empty_until_enabled() -> None:
    assert SmsGenerator().render(specification()) == {}


def test_sms_generator_renders_generated_runtime_contract() -> None:
    files = SmsGenerator().render(specification(enabled=True))
    root = PurePosixPath("src", "kis_auto_trading", "infrastructure", "sms")
    assert set(files) == {root / "__init__.py", root / "config.py", root / "fake.py", root / "protocol.py", root / "service.py", root / "solapi.py"}
    assert "SOLAPI_API_KEY" in files[root / "config.py"]
    assert "class SolapiSmsDelivery:" in files[root / "solapi.py"]
    assert '"solapi>=5,<6"' in FastAPIProjectGenerator().render(
        specification(enabled=True)
    )[PurePosixPath("pyproject.toml")]
    for path, source in files.items(): ast.parse(source, filename=path.as_posix())


@pytest.mark.anyio
async def test_generated_sms_uses_fake_without_external_delivery(tmp_path: Path) -> None:
    value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    for job_id, generator in [("project", FastAPIProjectGenerator()), ("sms", SmsGenerator())]:
        rendered = generator.render(value)
        GenerationPlanApplier().apply(job_id=job_id, plan=GenerationPlanResolver().resolve(generator.plan(value), workspace), rendered_files=rendered, workspace=workspace)
    code = """import asyncio, sys
sys.path.insert(0, 'src')
from kis_auto_trading.infrastructure.sms import FakeSmsDelivery, SmsMessage
async def verify():
    delivery = FakeSmsDelivery()
    receipt = await delivery.send(SmsMessage('01012345678', 'hello'))
    assert receipt.group_id == 'fake-1'
    assert delivery.messages[0].to == '01012345678'
asyncio.run(verify())
"""
    result = await AsyncioProcessRunner().run((sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10)
    assert result.succeeded, result.stderr
