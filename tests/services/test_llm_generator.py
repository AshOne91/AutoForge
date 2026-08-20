import ast
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    LlmSpec,
    ProjectInfo,
    ProjectSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.llm import LlmGenerator


def specification(*, enabled: bool = False) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(name="KIS", package_name="kis_auto_trading", version="0.1.0"),
        application=ApplicationSpec(),
        tooling=ToolingSpec(llm=LlmSpec(enabled=enabled, model="gpt-test")),
    )


def test_llm_generator_is_empty_until_enabled() -> None:
    assert LlmGenerator().render(specification()) == {}


def test_llm_generator_requires_a_model_when_enabled() -> None:
    with pytest.raises(ValueError, match="tooling.llm.model"):
        LlmSpec(enabled=True)


def test_llm_generator_renders_generated_runtime_contract() -> None:
    files = LlmGenerator().render(specification(enabled=True))
    root = PurePosixPath("src", "kis_auto_trading", "infrastructure", "llm")
    assert set(files) == {
        root / "__init__.py", root / "config.py", root / "fake.py",
        root / "openai_client.py", root / "protocol.py", root / "service.py",
    }
    assert "OPENAI_API_KEY" in files[root / "config.py"]
    assert "store=False" in files[root / "openai_client.py"]
    assert '"openai>=1,<3"' in FastAPIProjectGenerator().render(
        specification(enabled=True)
    )[PurePosixPath("pyproject.toml")]
    assert '"openai>=1,<3"' in FastAPIProjectGenerator().render(
        specification(enabled=True)
    )[PurePosixPath("pyproject.toml")]
    assert '"openai>=1,<3"' in FastAPIProjectGenerator().render(
        specification(enabled=True)
    )[PurePosixPath("pyproject.toml")]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


@pytest.mark.anyio
async def test_generated_llm_uses_openai_responses_contract(tmp_path: Path) -> None:
    value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    for job_id, generator in [("project", FastAPIProjectGenerator()), ("llm", LlmGenerator())]:
        rendered = generator.render(value)
        GenerationPlanApplier().apply(job_id=job_id, plan=GenerationPlanResolver().resolve(generator.plan(value), workspace), rendered_files=rendered, workspace=workspace)
    code = """import asyncio, sys, types
sys.path.insert(0, 'src')
openai = types.ModuleType('openai')
requests = []
class Responses:
    async def create(self, **kwargs):
        requests.append(kwargs)
        return types.SimpleNamespace(output_text='answer', id='resp_1')
class AsyncOpenAI:
    def __init__(self, **kwargs): self.responses = Responses()
    async def close(self): pass
openai.AsyncOpenAI = AsyncOpenAI
sys.modules['openai'] = openai
from kis_auto_trading.infrastructure.llm import LlmConfig, LlmMessage, OpenAIResponsesClient
async def verify():
    client = OpenAIResponsesClient(LlmConfig('secret', 'gpt-test'))
    response = await client.respond([LlmMessage('user', 'hello')], instructions='brief')
    assert response.content == 'answer'
    assert requests == [{'model': 'gpt-test', 'instructions': 'brief', 'input': [{'role': 'user', 'content': 'hello'}], 'store': False}]
asyncio.run(verify())
"""
    result = await AsyncioProcessRunner().run((sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10)
    assert result.succeeded, result.stderr
