import os
import socket
import uuid
from pathlib import Path, PurePosixPath

import anyio
import pytest
import yaml

from autoforge.core.specification import (
    ApplicationSpec,
    ProjectInfo,
    ProjectSpec,
    RagSpec,
    ToolingSpec,
)
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation.rag import RagInfrastructureGenerator


def specification(
    *,
    enabled: bool = False,
    search_backend: str = "elasticsearch",
    search_mode: str = "standalone",
    host_port_base: int = 49400,
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
            rag=RagSpec(
                enabled=enabled,
                search_backend=search_backend,
                search_mode=search_mode,
                host_port_base=host_port_base,
            )
        ),
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
    assert "RAG_SEARCH_BACKEND=elasticsearch" in environment
    assert "RAG_SEARCH_URL=http://elasticsearch:9200" in environment
    assert "OLLAMA_BASE_URL=http://ollama:11434" in environment
    assert "RAG_NETWORK_NAME=kis_auto_trading-rag" in environment
    assert "no model is downloaded automatically" in readme
    assert "docker network create kis_auto_trading-rag" in readme
    parsed = yaml.safe_load(compose)
    assert set(parsed["services"]) == {"qdrant", "elasticsearch", "ollama"}
    assert parsed["services"]["ollama"]["profiles"] == ["inference"]
    assert all(
        service["restart"] == "unless-stopped"
        for service in parsed["services"].values()
    )
    assert all("healthcheck" in service for service in parsed["services"].values())
    assert parsed["services"]["qdrant"]["healthcheck"]["test"] == [
        "CMD-SHELL",
        "bash -c 'echo > /dev/tcp/127.0.0.1/6333'",
    ]
    assert parsed["networks"]["rag"] == {
        "name": "${RAG_NETWORK_NAME:-kis_auto_trading-rag}",
        "external": True,
    }
    assert all(service["networks"] == ["rag"] for service in parsed["services"].values())


def test_rag_generator_renders_opensearch_instead_of_elasticsearch() -> None:
    files = RagInfrastructureGenerator().render(
        specification(enabled=True, search_backend="opensearch")
    )

    compose = files[PurePosixPath("deploy", "rag", "compose.rag.yaml")]
    environment = files[PurePosixPath("deploy", "rag", ".env.example")]
    parsed = yaml.safe_load(compose)

    assert "opensearchproject/opensearch:2.19.6" in compose
    assert "elasticsearch" not in parsed["services"]
    assert set(parsed["services"]) == {"qdrant", "opensearch", "ollama"}
    assert parsed["services"]["opensearch"]["environment"] == {
        "discovery.type": "single-node",
        "DISABLE_INSTALL_DEMO_CONFIG": "true",
        "DISABLE_SECURITY_PLUGIN": "true",
        "OPENSEARCH_JAVA_OPTS": "-Xms512m -Xmx512m",
    }
    assert "RAG_SEARCH_BACKEND=opensearch" in environment
    assert "RAG_SEARCH_URL=http://opensearch:9200" in environment


def test_rag_generator_renders_clustered_elasticsearch_behind_stable_endpoint() -> None:
    files = RagInfrastructureGenerator().render(
        specification(enabled=True, search_mode="cluster")
    )
    compose = files[PurePosixPath("deploy", "rag", "compose.rag.yaml")]
    environment = files[PurePosixPath("deploy", "rag", ".env.example")]
    proxy = files[PurePosixPath("deploy", "rag", "nginx", "search.conf")]
    readme = files[PurePosixPath("deploy", "rag", "README.md")]
    parsed = yaml.safe_load(compose)

    assert set(parsed["services"]) == {
        "qdrant",
        "search",
        "elasticsearch-1",
        "elasticsearch-2",
        "elasticsearch-3",
        "ollama",
    }
    assert "discovery.type" not in compose
    assert parsed["services"]["elasticsearch-1"]["environment"][
        "discovery.seed_hosts"
    ] == "elasticsearch-1,elasticsearch-2,elasticsearch-3"
    assert parsed["services"]["search"]["depends_on"]["elasticsearch-3"] == {
        "condition": "service_healthy"
    }
    assert "RAG_SEARCH_URL=http://search:9200" in environment
    assert "RAG_SEARCH_PORT=49460" in environment
    assert "proxy_next_upstream_tries 3" in proxy
    assert "three search members" in readme
    assert set(parsed["volumes"]) >= {
        "rag-elasticsearch-1-data",
        "rag-elasticsearch-2-data",
        "rag-elasticsearch-3-data",
    }


def test_rag_generator_renders_clustered_opensearch_behind_stable_endpoint() -> None:
    files = RagInfrastructureGenerator().render(
        specification(
            enabled=True,
            search_backend="opensearch",
            search_mode="cluster",
        )
    )
    compose = files[PurePosixPath("deploy", "rag", "compose.rag.yaml")]
    parsed = yaml.safe_load(compose)

    environment = parsed["services"]["opensearch-1"]["environment"]
    assert environment["cluster.initial_cluster_manager_nodes"] == (
        "opensearch-1,opensearch-2,opensearch-3"
    )
    assert parsed["services"]["opensearch-1"]["ulimits"]["nofile"]["soft"] == 65536
    assert "opensearch-3:9200" in files[
        PurePosixPath("deploy", "rag", "nginx", "search.conf")
    ]


@pytest.mark.integration
@pytest.mark.anyio
async def test_clustered_elasticsearch_recovers_search_after_member_stops(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_RAG_SEARCH_CLUSTER_INTEGRATION") != "1":
        pytest.skip("set AUTOFORGE_DOCKER_RAG_SEARCH_CLUSTER_INTEGRATION=1 to run Docker")

    host_port_base = next(
        base
        for base in range(49200, 65500, 100)
        if all(_port_is_available(port) for port in (base + 50, base + 51, base + 60))
    )
    package_name = f"rag_ha_{uuid.uuid4().hex}"
    files = RagInfrastructureGenerator().render(
        specification(
            enabled=True,
            search_mode="cluster",
            host_port_base=host_port_base,
        ).model_copy(
            update={
                "project": ProjectInfo(
                    name="RAG Search HA",
                    package_name=package_name,
                    version="0.1.0",
                )
            }
        )
    )
    for relative_path, content in files.items():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    rag_dir = tmp_path / "deploy" / "rag"
    (rag_dir / ".env").write_text(
        files[PurePosixPath("deploy", "rag", ".env.example")], encoding="utf-8"
    )
    compose = (
        "docker",
        "compose",
        "--env-file",
        "deploy/rag/.env",
        "-f",
        "deploy/rag/compose.rag.yaml",
        "--profile",
        "rag",
    )
    network = f"{package_name}-rag"
    runner = AsyncioProcessRunner()
    try:
        result = await runner.run(
            ("docker", "network", "create", network), cwd=tmp_path, timeout_seconds=20
        )
        assert result.succeeded, result.stderr
        result = await runner.run(
            (*compose, "up", "--detach"), cwd=tmp_path, timeout_seconds=240
        )
        assert result.succeeded, result.stderr
        for _ in range(45):
            result = await runner.run(
                (
                    *compose,
                    "exec",
                    "-T",
                    "elasticsearch-2",
                    "curl",
                    "--fail",
                    "--silent",
                    "http://search:9200/_cluster/health?wait_for_status=yellow&timeout=1s",
                ),
                cwd=tmp_path,
                timeout_seconds=10,
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
                "elasticsearch-2",
                "curl",
                "--fail",
                "--silent",
                "-X",
                "PUT",
                "http://search:9200/ha-check",
                "-H",
                "Content-Type: application/json",
                "-d",
                '{"settings":{"number_of_replicas":1}}',
            ),
            cwd=tmp_path,
            timeout_seconds=20,
        )
        assert result.succeeded, result.stderr
        result = await runner.run(
            (
                *compose,
                "exec",
                "-T",
                "elasticsearch-2",
                "curl",
                "--fail",
                "--silent",
                "-X",
                "POST",
                "http://search:9200/ha-check/_doc/1?refresh=true",
                "-H",
                "Content-Type: application/json",
                "-d",
                '{"message":"ha-check"}',
            ),
            cwd=tmp_path,
            timeout_seconds=20,
        )
        assert result.succeeded, result.stderr
        result = await runner.run(
            (*compose, "stop", "elasticsearch-1"), cwd=tmp_path, timeout_seconds=30
        )
        assert result.succeeded, result.stderr
        for _ in range(30):
            result = await runner.run(
                (
                    *compose,
                    "exec",
                    "-T",
                    "elasticsearch-2",
                    "curl",
                    "--fail",
                    "--silent",
                    "http://search:9200/ha-check/_doc/1",
                ),
                cwd=tmp_path,
                timeout_seconds=10,
            )
            if result.succeeded:
                break
            await anyio.sleep(2)
        assert result.succeeded, result.stderr
        assert '"message":"ha-check"' in result.stdout
    finally:
        await runner.run(
            (*compose, "down", "--volumes", "--remove-orphans"),
            cwd=tmp_path,
            timeout_seconds=180,
        )
        await runner.run(
            ("docker", "network", "rm", network), cwd=tmp_path, timeout_seconds=30
        )


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def test_rag_generator_plan_marks_all_outputs_generated() -> None:
    plan = RagInfrastructureGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 3
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:rag_infrastructure"}
