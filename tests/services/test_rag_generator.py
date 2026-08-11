from pathlib import PurePosixPath

import yaml

from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
    RagSpec,
    ToolingSpec,
)
from autoforge.services.generation.rag import RagInfrastructureGenerator


def specification(*, enabled: bool = False) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
        tooling=ToolingSpec(rag=RagSpec(enabled=enabled)),
    )


def test_rag_generator_is_empty_until_enabled() -> None:
    assert RagInfrastructureGenerator().render(specification()) == {}


def test_rag_generator_renders_opt_in_local_services() -> None:
    files = RagInfrastructureGenerator().render(specification(enabled=True))

    compose = files[PurePosixPath("deploy", "rag", "compose.rag.yaml")]
    environment = files[PurePosixPath("deploy", "rag", ".env.example")]
    readme = files[PurePosixPath("deploy", "rag", "README.md")]

    assert "qdrant/qdrant:v1.18.3" in compose
    assert "docker.elastic.co/elasticsearch/elasticsearch:8.19.17" in compose
    assert "ollama/ollama:0.32.5" in compose
    assert '"${LOCAL_BIND_ADDRESS:-127.0.0.1}:${QDRANT_HTTP_PORT:-49450}:6333"' in compose
    assert "QDRANT_URL=http://qdrant:6333" in environment
    assert "ELASTICSEARCH_URL=http://elasticsearch:9200" in environment
    assert "OLLAMA_BASE_URL=http://ollama:11434" in environment
    assert "no model is downloaded automatically" in readme
    parsed = yaml.safe_load(compose)
    assert set(parsed["services"]) == {"qdrant", "elasticsearch", "ollama"}
    assert parsed["services"]["ollama"]["profiles"] == ["inference"]


def test_rag_generator_plan_marks_all_outputs_generated() -> None:
    plan = RagInfrastructureGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 3
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:rag_infrastructure"}
