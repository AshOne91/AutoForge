import json
import os
import socket
import uuid
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
    qdrant_mode: str = "standalone",
    ollama_mode: str = "standalone",
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
                qdrant_mode=qdrant_mode,
                ollama_mode=ollama_mode,
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


def test_rag_generator_renders_clustered_qdrant_behind_stable_endpoint() -> None:
    files = RagInfrastructureGenerator().render(
        specification(enabled=True, qdrant_mode="cluster")
    )
    compose = files[PurePosixPath("deploy", "rag", "compose.rag.yaml")]
    proxy = files[PurePosixPath("deploy", "rag", "nginx", "qdrant.conf")]
    readme = files[PurePosixPath("deploy", "rag", "README.md")]
    parsed = yaml.safe_load(compose)

    assert set(parsed["services"]) == {
        "qdrant",
        "qdrant-1",
        "qdrant-2",
        "qdrant-3",
        "elasticsearch",
        "ollama",
    }
    assert parsed["services"]["qdrant"]["depends_on"]["qdrant-3"] == {
        "condition": "service_healthy"
    }
    assert parsed["services"]["qdrant-1"]["command"] == (
        "./qdrant --uri http://qdrant-1:6335"
    )
    assert "--bootstrap http://qdrant-1:6335" in parsed["services"]["qdrant-2"][
        "command"
    ]
    assert parsed["services"]["qdrant-2"]["environment"] == {
        "QDRANT__CLUSTER__ENABLED": "true"
    }
    assert "qdrant-3:6333" in proxy
    assert "qdrant-3:6334" in proxy
    assert proxy.count("server qdrant-1:6334") == 1
    assert "replication_factor" in readme
    assert set(parsed["volumes"]) >= {
        "qdrant-1-storage",
        "qdrant-2-storage",
        "qdrant-3-storage",
    }


def test_rag_generator_renders_replicated_ollama_behind_stable_endpoint() -> None:
    files = RagInfrastructureGenerator().render(
        specification(enabled=True, ollama_mode="replicated")
    )
    compose = files[PurePosixPath("deploy", "rag", "compose.rag.yaml")]
    proxy = files[PurePosixPath("deploy", "rag", "nginx", "ollama.conf")]
    readme = files[PurePosixPath("deploy", "rag", "README.md")]
    parsed = yaml.safe_load(compose)

    assert set(parsed["services"]) == {
        "qdrant",
        "elasticsearch",
        "ollama",
        "ollama-1",
        "ollama-2",
        "ollama-3",
    }
    assert parsed["services"]["ollama"]["depends_on"]["ollama-3"] == {
        "condition": "service_healthy"
    }
    assert parsed["services"]["ollama-1"]["volumes"] == [
        "ollama-1-data:/root/.ollama"
    ]
    assert parsed["services"]["ollama-2"]["volumes"] == [
        "ollama-2-data:/root/.ollama"
    ]
    assert "proxy_request_buffering off" in proxy
    assert "proxy_read_timeout 3600s" in proxy
    assert "must pull each selected model" in readme
    assert "exec ollama-$_ ollama pull" in readme
    assert set(parsed["volumes"]) >= {
        "ollama-1-data",
        "ollama-2-data",
        "ollama-3-data",
    }


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
async def test_clustered_qdrant_reads_and_writes_after_member_stops(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_QDRANT_CLUSTER_INTEGRATION") != "1":
        pytest.skip("set AUTOFORGE_DOCKER_QDRANT_CLUSTER_INTEGRATION=1 to run Docker")

    host_port_base = next(
        base
        for base in range(49200, 65500, 100)
        if all(_port_is_available(port) for port in (base + 50, base + 51))
    )
    package_name = f"qdrant_ha_{uuid.uuid4().hex}"
    files = RagInfrastructureGenerator().render(
        specification(
            enabled=True,
            qdrant_mode="cluster",
            host_port_base=host_port_base,
        ).model_copy(
            update={
                "project": ProjectInfo(
                    name="Qdrant HA",
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
    endpoint = f"http://127.0.0.1:{host_port_base + 50}"
    runner = AsyncioProcessRunner()
    try:
        result = await runner.run(
            ("docker", "network", "create", network), cwd=tmp_path, timeout_seconds=20
        )
        assert result.succeeded, result.stderr
        result = await runner.run(
            (*compose, "up", "--detach", "qdrant"), cwd=tmp_path, timeout_seconds=180
        )
        assert result.succeeded, result.stderr
        cluster: dict[str, object] = {}
        for _ in range(45):
            try:
                cluster = await anyio.to_thread.run_sync(
                    _request_json, f"{endpoint}/cluster"
                )
            except (HTTPError, URLError, TimeoutError):
                await anyio.sleep(2)
                continue
            if (
                cluster["result"]["status"] == "enabled"
                and len(cluster["result"]["peers"]) == 3
            ):
                break
            await anyio.sleep(2)
        else:
            pytest.fail(f"Qdrant cluster did not form: {cluster}")
        await anyio.to_thread.run_sync(
            _request_json,
            f"{endpoint}/collections/ha-check?wait=true",
            "PUT",
            {
                "vectors": {"size": 4, "distance": "Cosine"},
                "shard_number": 3,
                "replication_factor": 3,
                "write_consistency_factor": 2,
            },
        )
        await anyio.to_thread.run_sync(
            _request_json,
            f"{endpoint}/collections/ha-check/points?wait=true",
            "PUT",
            {"points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}]},
        )
        result = await runner.run(
            (*compose, "stop", "qdrant-1"), cwd=tmp_path, timeout_seconds=30
        )
        assert result.succeeded, result.stderr
        for _ in range(30):
            try:
                response = await anyio.to_thread.run_sync(
                    _request_json,
                    f"{endpoint}/collections/ha-check/points?wait=true",
                    "PUT",
                    {"points": [{"id": 2, "vector": [0.4, 0.3, 0.2, 0.1]}]},
                )
            except (HTTPError, URLError, TimeoutError):
                await anyio.sleep(2)
                continue
            if response.get("status") == "ok":
                break
            await anyio.sleep(2)
        else:
            pytest.fail("Qdrant write was unavailable after member stop")
        for _ in range(30):
            try:
                point = await anyio.to_thread.run_sync(
                    _request_json, f"{endpoint}/collections/ha-check/points/2"
                )
            except (HTTPError, URLError, TimeoutError):
                await anyio.sleep(2)
                continue
            if point.get("result", {}).get("id") == 2:
                break
            await anyio.sleep(2)
        else:
            pytest.fail("Qdrant point written after member stop was unavailable")
        for _ in range(30):
            try:
                point = await anyio.to_thread.run_sync(
                    _request_json, f"{endpoint}/collections/ha-check/points/1"
                )
            except (HTTPError, URLError, TimeoutError):
                await anyio.sleep(2)
                continue
            if point.get("result", {}).get("id") == 1:
                break
            await anyio.sleep(2)
        else:
            pytest.fail("replicated Qdrant point was unavailable after member stop")
        result = await runner.run(
            (*compose, "start", "qdrant-1"), cwd=tmp_path, timeout_seconds=30
        )
        assert result.succeeded, result.stderr
        collection_cluster: dict[str, object] = {}
        for _ in range(45):
            try:
                cluster = await anyio.to_thread.run_sync(
                    _request_json, f"{endpoint}/cluster"
                )
                collection_cluster = await anyio.to_thread.run_sync(
                    _request_json, f"{endpoint}/collections/ha-check/cluster"
                )
            except (HTTPError, URLError, TimeoutError):
                await anyio.sleep(2)
                continue
            distribution = collection_cluster.get("result", {})
            replicas = distribution.get("local_shards", []) + distribution.get(
                "remote_shards", []
            )
            if (
                len(cluster.get("result", {}).get("peers", {})) == 3
                and len(replicas) == 9
                and all(replica.get("state") == "Active" for replica in replicas)
                and not distribution.get("shard_transfers")
            ):
                break
            await anyio.sleep(2)
        else:
            pytest.fail(
                "Qdrant peer or collection replicas did not recover: "
                f"cluster={cluster}, collection={collection_cluster}"
            )
        point = await anyio.to_thread.run_sync(
            _request_json, f"{endpoint}/collections/ha-check/points/2"
        )
        assert point.get("result", {}).get("id") == 2
    finally:
        await runner.run(
            (*compose, "down", "--volumes", "--remove-orphans"),
            cwd=tmp_path,
            timeout_seconds=180,
        )
        await runner.run(
            ("docker", "network", "rm", network), cwd=tmp_path, timeout_seconds=30
        )


@pytest.mark.integration
@pytest.mark.anyio
async def test_replicated_ollama_recovers_member_and_proxy_readiness(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_OLLAMA_REPLICATED_INTEGRATION") != "1":
        pytest.skip("set AUTOFORGE_DOCKER_OLLAMA_REPLICATED_INTEGRATION=1 to run Docker")

    host_port_base = next(
        base
        for base in range(49200, 65500, 100)
        if _port_is_available(base + 70)
    )
    package_name = f"ollama_ha_{uuid.uuid4().hex}"
    files = RagInfrastructureGenerator().render(
        specification(
            enabled=True,
            ollama_mode="replicated",
            host_port_base=host_port_base,
        ).model_copy(
            update={
                "project": ProjectInfo(
                    name="Ollama HA",
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
        "inference",
    )
    network = f"{package_name}-rag"
    endpoint = f"http://127.0.0.1:{host_port_base + 70}/api/tags"
    runner = AsyncioProcessRunner()
    try:
        result = await runner.run(
            ("docker", "network", "create", network), cwd=tmp_path, timeout_seconds=20
        )
        assert result.succeeded, result.stderr
        result = await runner.run(
            (*compose, "up", "--detach", "ollama"), cwd=tmp_path, timeout_seconds=180
        )
        assert result.succeeded, result.stderr
        for _ in range(30):
            try:
                tags = await anyio.to_thread.run_sync(_request_json, endpoint)
            except (HTTPError, URLError, TimeoutError):
                await anyio.sleep(2)
                continue
            if "models" in tags:
                break
            await anyio.sleep(2)
        else:
            pytest.fail("replicated Ollama readiness did not become available")
        result = await runner.run(
            (*compose, "stop", "ollama-1"), cwd=tmp_path, timeout_seconds=30
        )
        assert result.succeeded, result.stderr
        for _ in range(30):
            try:
                tags = await anyio.to_thread.run_sync(_request_json, endpoint)
            except (HTTPError, URLError, TimeoutError):
                await anyio.sleep(2)
                continue
            if "models" in tags:
                break
            await anyio.sleep(2)
        else:
            pytest.fail("Ollama readiness was unavailable after member stop")
        result = await runner.run(
            (*compose, "start", "ollama-1"), cwd=tmp_path, timeout_seconds=30
        )
        assert result.succeeded, result.stderr
        for _ in range(30):
            result = await runner.run(
                (*compose, "ps", "--quiet", "ollama-1", "ollama-2", "ollama-3"),
                cwd=tmp_path,
                timeout_seconds=10,
            )
            container_ids = result.stdout.splitlines() if result.succeeded else []
            if len(container_ids) == 3:
                result = await runner.run(
                    (
                        "docker",
                        "inspect",
                        "--format",
                        "{{.State.Health.Status}}",
                        *container_ids,
                    ),
                    cwd=tmp_path,
                    timeout_seconds=10,
                )
                if result.succeeded and result.stdout.splitlines() == [
                    "healthy",
                    "healthy",
                    "healthy",
                ]:
                    break
            await anyio.sleep(2)
        else:
            pytest.fail(f"Ollama members did not recover: {result.stdout} {result.stderr}")
        tags = await anyio.to_thread.run_sync(_request_json, endpoint)
        assert "models" in tags
    finally:
        await runner.run(
            (*compose, "down", "--volumes", "--remove-orphans"),
            cwd=tmp_path,
            timeout_seconds=180,
        )
        await runner.run(
            ("docker", "network", "rm", network), cwd=tmp_path, timeout_seconds=30
        )


@pytest.mark.integration
@pytest.mark.anyio
@pytest.mark.parametrize("search_backend", ("elasticsearch", "opensearch"))
async def test_clustered_search_backend_reads_and_writes_after_member_stops(
    tmp_path: Path,
    search_backend: str,
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
            search_backend=search_backend,
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
                    f"{search_backend}-2",
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
                f"{search_backend}-2",
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
                f"{search_backend}-2",
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
            (*compose, "stop", f"{search_backend}-1"), cwd=tmp_path, timeout_seconds=30
        )
        assert result.succeeded, result.stderr
        for _ in range(30):
            result = await runner.run(
                (
                    *compose,
                    "exec",
                    "-T",
                    f"{search_backend}-2",
                    "curl",
                    "--fail",
                    "--silent",
                    "-X",
                    "POST",
                    "http://search:9200/ha-check/_doc/2?refresh=true",
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    '{"message":"ha-write"}',
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
                f"{search_backend}-2",
                "curl",
                "--fail",
                "--silent",
                "http://search:9200/ha-check/_search?q=message:ha-write",
            ),
            cwd=tmp_path,
            timeout_seconds=20,
        )
        assert result.succeeded, result.stderr
        assert '"message":"ha-write"' in result.stdout
        for _ in range(30):
            result = await runner.run(
                (
                    *compose,
                    "exec",
                    "-T",
                    f"{search_backend}-2",
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
        result = await runner.run(
            (*compose, "start", f"{search_backend}-1"), cwd=tmp_path, timeout_seconds=30
        )
        assert result.succeeded, result.stderr
        health: dict[str, object] = {}
        for _ in range(30):
            result = await runner.run(
                (
                    *compose,
                    "exec",
                    "-T",
                    f"{search_backend}-2",
                    "curl",
                    "--fail",
                    "--silent",
                    "http://search:9200/_cluster/health/ha-check?wait_for_status=green&wait_for_nodes=3&timeout=2s",
                ),
                cwd=tmp_path,
                timeout_seconds=10,
            )
            if result.succeeded:
                health = json.loads(result.stdout)
                if (
                    health.get("status") == "green"
                    and health.get("number_of_nodes") == 3
                    and health.get("unassigned_shards") == 0
                ):
                    break
            await anyio.sleep(2)
        assert result.succeeded, result.stderr
        assert health.get("status") == "green"
        assert health.get("number_of_nodes") == 3
        assert health.get("unassigned_shards") == 0
        result = await runner.run(
            (
                *compose,
                "exec",
                "-T",
                f"{search_backend}-2",
                "curl",
                "--fail",
                "--silent",
                "http://search:9200/ha-check/_search?q=message:ha-write",
            ),
            cwd=tmp_path,
            timeout_seconds=20,
        )
        assert result.succeeded, result.stderr
        assert '"message":"ha-write"' in result.stdout
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


def _request_json(
    url: str, method: str = "GET", payload: dict[str, object] | None = None
) -> dict[str, object]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def test_rag_generator_plan_marks_all_outputs_generated() -> None:
    plan = RagInfrastructureGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 3
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:rag_infrastructure"}
