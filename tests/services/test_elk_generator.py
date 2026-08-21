import json
import os
import socket
import uuid
from http.client import RemoteDisconnected
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import anyio
import pytest
import yaml

from autoforge.core.specification import (
    ApplicationSpec,
    ElkSpec,
    ProjectInfo,
    ProjectSpec,
    ToolingSpec,
)
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation.elk import ElkStackGenerator


def specification(
    *,
    enabled: bool = False,
    elasticsearch_mode: str = "standalone",
    host_port_base: int = 49600,
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
            elk=ElkSpec(
                enabled=enabled,
                elasticsearch_mode=elasticsearch_mode,
                host_port_base=host_port_base,
            )
        ),
    )


def test_elk_generator_is_empty_until_enabled() -> None:
    assert ElkStackGenerator().render(specification()) == {}


def test_elk_generator_renders_development_overlay_and_filebeat_config() -> None:
    files = ElkStackGenerator().render(specification(enabled=True))

    compose = files[PurePosixPath("deploy", "observability", "compose.elk.yaml")]
    filebeat = files[PurePosixPath("deploy", "observability", "filebeat.yml")]
    readme = files[PurePosixPath("deploy", "observability", "README.md")]

    assert "docker.elastic.co/elasticsearch/elasticsearch:8.19.17" in compose
    assert "xpack.security.enabled: \"false\"" in compose
    assert "${LOG_ROOT:-../logs}:/var/log/application:ro" in compose
    assert "${FILEBEAT_CONFIG:-../deploy/observability/filebeat.yml}" in compose
    assert 'ELASTICSEARCH_PORT:-49600' in compose
    assert 'KIBANA_PORT:-49601' in compose
    assert 'default `49601`' in readme
    assert '127.0.0.1:49600/filebeat-*/_search' in readme
    assert "type: filestream" in filebeat
    assert "/var/log/application/*.log" in filebeat
    assert "/var/log/application/*/*.log" in filebeat
    assert "ndjson:" in filebeat
    assert "filebeat-data:/usr/share/filebeat/data" in compose
    assert "news_collection_retries_exhausted" in readme
    assert "This is a local development profile." in readme
    parsed = yaml.safe_load(compose)
    assert set(parsed["services"]) == {
        "elasticsearch",
        "kibana",
        "filebeat",
    }
    assert all(
        service["restart"] == "unless-stopped"
        for service in parsed["services"].values()
    )
    assert all("healthcheck" in service for service in parsed["services"].values())
    assert parsed["services"]["filebeat"]["healthcheck"]["test"] == [
        "CMD",
        "filebeat",
        "test",
        "config",
        "-e",
        "--strict.perms=false",
        "-c",
        "/usr/share/filebeat/filebeat.yml",
    ]
    assert parsed["services"]["kibana"]["depends_on"]["elasticsearch"]["condition"] == "service_healthy"
    assert parsed["services"]["filebeat"]["depends_on"]["elasticsearch"]["condition"] == "service_healthy"
    assert "name" not in parsed


def test_elk_generator_renders_clustered_storage_behind_stable_endpoint() -> None:
    files = ElkStackGenerator().render(
        specification(enabled=True, elasticsearch_mode="cluster")
    )
    compose = files[PurePosixPath("deploy", "observability", "compose.elk.yaml")]
    proxy = files[
        PurePosixPath("deploy", "observability", "nginx", "elasticsearch.conf")
    ]
    filebeat = files[PurePosixPath("deploy", "observability", "filebeat.yml")]
    parsed = yaml.safe_load(compose)

    assert set(parsed["services"]) == {
        "elasticsearch",
        "elasticsearch-1",
        "elasticsearch-2",
        "elasticsearch-3",
        "kibana",
        "filebeat",
    }
    assert "discovery.type" not in compose
    assert parsed["services"]["elasticsearch"]["depends_on"]["elasticsearch-3"] == {
        "condition": "service_healthy"
    }
    assert parsed["services"]["kibana"]["environment"]["ELASTICSEARCH_HOSTS"] == (
        "http://elasticsearch:9200"
    )
    assert 'hosts: ["http://elasticsearch:9200"]' in filebeat
    assert "elasticsearch-3:9200" in proxy
    assert set(parsed["volumes"]) >= {
        "elasticsearch-1-data",
        "elasticsearch-2-data",
        "elasticsearch-3-data",
    }


def test_elk_generator_plan_marks_all_outputs_generated() -> None:
    plan = ElkStackGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 3
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:elk"}


def test_clustered_elk_plan_includes_the_stable_proxy_config() -> None:
    plan = ElkStackGenerator().plan(
        specification(enabled=True, elasticsearch_mode="cluster")
    )

    assert {file.relative_path for file in plan.files} >= {
        PurePosixPath("deploy", "observability", "compose.elk.yaml"),
        PurePosixPath("deploy", "observability", "nginx", "elasticsearch.conf"),
    }


def test_elk_collector_mode_generates_filebeat_only() -> None:
    collector_spec = specification(enabled=True).model_copy(
        update={"tooling": ToolingSpec(elk=ElkSpec(enabled=True, mode="collector"))}
    )

    files = ElkStackGenerator().render(collector_spec)
    compose = yaml.safe_load(
        files[PurePosixPath("deploy", "observability", "compose.elk.yaml")]
    )
    filebeat = files[PurePosixPath("deploy", "observability", "filebeat.yml")]
    readme = files[PurePosixPath("deploy", "observability", "README.md")]

    assert set(compose["services"]) == {"filebeat"}
    assert "filebeat-data" in compose["volumes"]
    assert compose["services"]["filebeat"]["volumes"][:2] == [
        "${LOG_ROOT:-../../logs}:/var/log/application:ro",
        "${FILEBEAT_CONFIG:-../../deploy/observability/filebeat.yml}:/usr/share/filebeat/filebeat.yml:ro",
    ]
    assert "${ELASTICSEARCH_HOST}" in filebeat
    assert "collector-only" in readme


@pytest.mark.integration
@pytest.mark.anyio
async def test_clustered_elk_ingests_and_searches_logs_after_member_stops(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_ELK_CLUSTER_INTEGRATION") != "1":
        pytest.skip("set AUTOFORGE_DOCKER_ELK_CLUSTER_INTEGRATION=1 to run Docker")

    host_port_base = next(
        base
        for base in range(49600, 65500, 100)
        if all(_port_is_available(port) for port in (base, base + 1))
    )
    package_name = f"elk_ha_{uuid.uuid4().hex}"
    files = ElkStackGenerator().render(
        specification(
            enabled=True,
            elasticsearch_mode="cluster",
            host_port_base=host_port_base,
        ).model_copy(
            update={
                "project": ProjectInfo(
                    name="ELK HA",
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

    logs = tmp_path / "logs"
    logs.mkdir()
    marker = f"elk-ha-{uuid.uuid4().hex}"
    outage_marker = f"elk-ha-outage-{uuid.uuid4().hex}"
    compose = (
        "docker",
        "compose",
        "--project-name",
        package_name,
        "-f",
        "deploy/observability/compose.elk.yaml",
    )
    environment = {
        "ELASTICSEARCH_PORT": str(host_port_base),
        "KIBANA_PORT": str(host_port_base + 1),
        "LOG_ROOT": "../../logs",
        "FILEBEAT_CONFIG": "./filebeat.yml",
    }
    runner = AsyncioProcessRunner()
    try:
        result = await runner.run(
            (*compose, "up", "--detach"),
            cwd=tmp_path,
            timeout_seconds=240,
            environment=environment,
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
                    "http://elasticsearch:9200/_cluster/health?wait_for_nodes=3&timeout=1s",
                ),
                cwd=tmp_path,
                timeout_seconds=10,
                environment=environment,
            )
            if result.succeeded:
                break
            await anyio.sleep(2)
        assert result.succeeded, result.stderr

        (logs / "application.log").write_text(
            f'{{"event_type":"{marker}","message":"clustered elk"}}\n',
            encoding="utf-8",
        )
        query = (
            '{"query":{"term":{"event_type":"'
            f"{marker}"
            '"}}}'
        )
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
                    "-X",
                    "POST",
                    "http://elasticsearch:9200/_search",
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    query,
                ),
                cwd=tmp_path,
                timeout_seconds=20,
                environment=environment,
            )
            if marker in result.stdout:
                break
            await anyio.sleep(2)
        assert marker in result.stdout, result.stderr

        result = await runner.run(
            (*compose, "stop", "elasticsearch-1"),
            cwd=tmp_path,
            timeout_seconds=30,
            environment=environment,
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
                    "-X",
                    "POST",
                    "http://elasticsearch:9200/_search",
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    query,
                ),
                cwd=tmp_path,
                timeout_seconds=20,
                environment=environment,
            )
            if marker in result.stdout:
                break
            await anyio.sleep(2)
        assert marker in result.stdout, result.stderr

        with (logs / "application.log").open("a", encoding="utf-8") as log_file:
            log_file.write(
                f'{{"event_type":"{outage_marker}","message":"clustered elk outage write"}}\n'
            )
        outage_query = (
            '{"query":{"term":{"event_type":"'
            f"{outage_marker}"
            '"}}}'
        )
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
                    "-X",
                    "POST",
                    "http://elasticsearch:9200/_search",
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    outage_query,
                ),
                cwd=tmp_path,
                timeout_seconds=20,
                environment=environment,
            )
            if outage_marker in result.stdout:
                break
            await anyio.sleep(2)
        assert outage_marker in result.stdout, result.stderr

        kibana_status_url = f"http://127.0.0.1:{host_port_base + 1}/api/status"
        for _ in range(30):
            try:
                status = await anyio.to_thread.run_sync(
                    _get_status, kibana_status_url
                )
            except (HTTPError, RemoteDisconnected, URLError, TimeoutError):
                await anyio.sleep(2)
                continue
            if status == 200:
                break
            await anyio.sleep(2)
        else:
            pytest.fail("Kibana was unavailable after an Elasticsearch member stopped")
        result = await runner.run(
            (*compose, "start", "elasticsearch-1"),
            cwd=tmp_path,
            timeout_seconds=30,
            environment=environment,
        )
        assert result.succeeded, result.stderr
        health: dict[str, object] = {}
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
                    "http://elasticsearch:9200/_cluster/health?wait_for_status=green&wait_for_nodes=3&timeout=2s",
                ),
                cwd=tmp_path,
                timeout_seconds=10,
                environment=environment,
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
                "elasticsearch-2",
                "curl",
                "--fail",
                "--silent",
                "-X",
                "POST",
                "http://elasticsearch:9200/_search",
                "-H",
                "Content-Type: application/json",
                "-d",
                outage_query,
            ),
            cwd=tmp_path,
            timeout_seconds=20,
            environment=environment,
        )
        assert result.succeeded, result.stderr
        assert outage_marker in result.stdout
    finally:
        await runner.run(
            (*compose, "down", "--volumes", "--remove-orphans"),
            cwd=tmp_path,
            timeout_seconds=180,
            environment=environment,
        )


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _get_status(url: str) -> int:
    with urlopen(url, timeout=5) as response:
        return response.status
