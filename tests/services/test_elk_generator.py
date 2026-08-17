from pathlib import PurePosixPath

import yaml

from autoforge.core.specification import (
    ApplicationSpec,
    ElkSpec,
    ProjectInfo,
    ProjectSpec,
    ToolingSpec,
)
from autoforge.services.generation.elk import ElkStackGenerator


def specification(*, enabled: bool = False) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
        tooling=ToolingSpec(elk=ElkSpec(enabled=enabled)),
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


def test_elk_generator_plan_marks_all_outputs_generated() -> None:
    plan = ElkStackGenerator().plan(specification(enabled=True))

    assert len(plan.files) == 3
    assert {file.ownership.value for file in plan.files} == {"generated"}
    assert {file.source for file in plan.files} == {"project:elk"}


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
    assert "${ELASTICSEARCH_HOST}" in filebeat
    assert "collector-only" in readme
