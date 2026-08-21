import ast
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
    ToolingSpec,
    VectorStoreSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import GenerationPlanApplier, GenerationPlanResolver
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.vector_store import VectorStoreGenerator


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
            vector_store=VectorStoreSpec(
                enabled=enabled,
                url_environment="RAG_QDRANT_URL",
                api_key_environment="QDRANT_API_KEY",
                default_collection="news_vectors",
            )
        ),
    )


def test_vector_store_generator_is_empty_until_enabled() -> None:
    assert VectorStoreGenerator().render(specification()) == {}


def test_vector_store_generator_renders_qdrant_runtime_contract() -> None:
    files = VectorStoreGenerator().render(specification(enabled=True))
    root = PurePosixPath("src", "kis_auto_trading", "infrastructure", "vector_store")

    assert set(files) == {
        root / "__init__.py",
        root / "config.py",
        root / "fake.py",
        root / "protocol.py",
        root / "qdrant.py",
        root / "service.py",
    }
    assert "RAG_QDRANT_URL" in files[root / "config.py"]
    assert "QDRANT_API_KEY" in files[root / "config.py"]
    assert "class VectorStore:" in files[root / "service.py"]
    assert "class FakeVectorStoreClient:" in files[root / "fake.py"]
    assert "async def upsert_point" in files[root / "protocol.py"]
    assert "from typing import Protocol\n\ntype PointId = int | str" in files[
        root / "protocol.py"
    ]
    assert "'/readyz'" in files[root / "qdrant.py"]
    assert "points/query" in files[root / "qdrant.py"]
    for path, source in files.items():
        ast.parse(source, filename=path.as_posix())


def test_vector_store_plan_marks_runtime_contract_generated() -> None:
    plan = VectorStoreGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 6
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:kis_auto_trading:vector-store"}


def test_vector_store_makes_httpx_a_runtime_dependency() -> None:
    files = FastAPIProjectGenerator().render(specification(enabled=True))
    runtime_dependencies, _ = files[PurePosixPath("pyproject.toml")].split(
        "[project.optional-dependencies]"
    )

    assert '    "httpx>=0.28,<1",' in runtime_dependencies


@pytest.mark.anyio
async def test_generated_vector_store_fake_is_deterministic(tmp_path: Path) -> None:
    specification_value = specification(enabled=True)
    workspace = Workspace(tmp_path)
    project_generator = FastAPIProjectGenerator()
    vector_store_generator = VectorStoreGenerator()

    for job_id, generator in [
        ("project-job", project_generator),
        ("vector-store-job", vector_store_generator),
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
        "from kis_auto_trading.infrastructure.vector_store import (\n"
        "    FakeVectorStoreClient, VectorStore,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    store = VectorStore(FakeVectorStoreClient(), 'news_vectors')\n"
        "    await store.health_check()\n"
        "    await store.upsert_point('b', [0.2], {'headline': 'B'})\n"
        "    await store.upsert_point('a', [0.1], {'headline': 'A'})\n"
        "    assert await store.get_point('a') == {\n"
        "        'id': 'a', 'vector': [0.1], 'payload': {'headline': 'A'}\n"
        "    }\n"
        "    assert [point['id'] for point in await store.query({})] == ['a', 'b']\n"
        "    await store.delete_point('a')\n"
        "    assert await store.get_point('a') is None\n"
        "    await store.aclose()\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", code), cwd=workspace.root, timeout_seconds=10
    )

    assert result.succeeded, result.stderr
