import ast
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
    SearchSpec,
    ToolingSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.search import SearchServiceGenerator


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
            search=SearchSpec(
                enabled=enabled,
                backend="opensearch",
                url_environment="RAG_SEARCH_URL",
                default_index="news_documents",
            )
        ),
    )


def test_search_service_generator_is_empty_until_enabled() -> None:
    assert SearchServiceGenerator().render(specification()) == {}


def test_search_service_generator_renders_generated_runtime_contract() -> None:
    files = SearchServiceGenerator().render(specification(enabled=True))
    root = PurePosixPath("src", "kis_auto_trading", "infrastructure", "search")

    assert set(files) == {
        root / "__init__.py",
        root / "config.py",
        root / "fake.py",
        root / "http_client.py",
        root / "protocol.py",
        root / "service.py",
    }
    assert "RAG_SEARCH_URL" in files[root / "config.py"]
    assert "DEFAULT_BACKEND: Final = \"opensearch\"" in files[root / "config.py"]
    assert "class SearchService:" in files[root / "service.py"]
    assert "class FakeSearchClient:" in files[root / "fake.py"]
    assert "async def health_check" in files[root / "protocol.py"]
    assert "httpx.AsyncClient" in files[root / "http_client.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_search_service_plan_marks_runtime_contract_generated() -> None:
    plan = SearchServiceGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 6
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:kis_auto_trading:search-service"}


def test_search_service_makes_httpx_a_runtime_dependency() -> None:
    files = FastAPIProjectGenerator().render(specification(enabled=True))
    runtime_dependencies, _ = files[PurePosixPath("pyproject.toml")].split(
        "[project.optional-dependencies]"
    )

    assert '    "httpx>=0.28,<1",' in runtime_dependencies


@pytest.mark.anyio
async def test_generated_search_fake_is_deterministic(tmp_path: Path) -> None:
    specification_value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    service_generator = SearchServiceGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("search-job", service_generator),
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
        "from kis_auto_trading.infrastructure.search import FakeSearchClient, SearchService\n"
        "\n"
        "async def verify():\n"
        "    service = SearchService(FakeSearchClient(), 'news_documents')\n"
        "    await service.health_check()\n"
        "    await service.index_document('b', {'headline': 'B'})\n"
        "    await service.index_document('a', {'headline': 'A'})\n"
        "    assert await service.search({'match_all': {}}) == [\n"
        "        {'headline': 'A'}, {'headline': 'B'}\n"
        "    ]\n"
        "    await service.delete_document('a')\n"
        "    assert await service.search({'match_all': {}}) == [{'headline': 'B'}]\n"
        "    await service.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr
