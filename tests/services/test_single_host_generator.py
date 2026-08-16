from pathlib import PurePosixPath

import pytest
import yaml
from pydantic import ValidationError

from autoforge.core.generation import FileOwnership, Generator, content_hash
from autoforge.core.specification import (
    ApplicationSpec,
    DatabaseStoreSpec,
    LocalEnvironmentSpec,
    ProjectInfo,
    ProjectSpec,
    SingleHostSpec,
    ToolingSpec,
)
from autoforge.services.generation.plugin_registry import (
    create_fastapi_generator_plugins,
)
from autoforge.services.generation.single_host import (
    SINGLE_HOST_GENERATOR_ID,
    SingleHostOperatingGenerator,
)


def single_host_specification(
    *,
    enabled: bool = False,
    application_replicas: int = 3,
    host_port_base: int | None = None,
    bootstrap_provider: str = "none",
) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(
            databases=[
                DatabaseStoreSpec(
                    name="identity", global_url_env="IDENTITY_DATABASE_URL"
                )
            ]
        ),
        tooling=ToolingSpec(
            local_environment=LocalEnvironmentSpec(
                enabled=True, application_enabled=True, host_port_base=host_port_base
            ),
            single_host=SingleHostSpec(
                enabled=enabled,
                application_replicas=application_replicas,
                bootstrap_provider=bootstrap_provider,
            ),
        ),
    )


def test_single_host_generator_satisfies_protocol() -> None:
    generator: Generator[ProjectSpec] = SingleHostOperatingGenerator()

    assert isinstance(generator, Generator)


def test_render_is_empty_until_single_host_is_enabled() -> None:
    assert SingleHostOperatingGenerator().render(single_host_specification()) == {}


def test_render_adds_public_proxy_and_application_replicas() -> None:
    files = SingleHostOperatingGenerator().render(
        single_host_specification(enabled=True, application_replicas=3)
    )

    assert set(files) == {
        PurePosixPath("deploy", "single-host", "compose.override.yml"),
        PurePosixPath("deploy", "single-host", "runtime.env.example"),
        PurePosixPath("deploy", "single-host", "nginx", "default.conf.template"),
        PurePosixPath("deploy", "single-host", "README.md"),
    }
    compose_text = files[
        PurePosixPath("deploy", "single-host", "compose.override.yml")
    ]
    compose = yaml.safe_load(compose_text.replace("!reset ", ""))
    runtime_environment = files[
        PurePosixPath("deploy", "single-host", "runtime.env.example")
    ]
    nginx = files[
        PurePosixPath("deploy", "single-host", "nginx", "default.conf.template")
    ]
    readme = files[PurePosixPath("deploy", "single-host", "README.md")]

    assert compose["services"]["application"]["deploy"]["replicas"] == 3
    assert compose["services"]["application"]["volumes"] == [
        "${LOG_ROOT:-../logs}:/app/logs"
    ]
    assert "ports: !reset []" in compose_text
    assert compose["services"]["nginx"]["restart"] == "unless-stopped"
    assert compose["services"]["nginx"]["depends_on"]["application"] == {
        "condition": "service_healthy"
    }
    assert "http://127.0.0.1/health" in compose_text
    assert "PUBLIC_BIND_ADDRESS=0.0.0.0" in runtime_environment
    assert "LOG_ROOT=../logs" in runtime_environment
    assert "resolver 127.0.0.11" in nginx
    assert "set $upstream ${UPSTREAM_HOST}:8000;" in nginx
    assert "--env-file environment/.env" in readme
    assert "port-collision" in readme
    assert "service-level HA" in readme
    assert "validate-ports --env-file environment/.env" in readme


def test_render_uses_local_port_block_for_single_host_proxy() -> None:
    files = SingleHostOperatingGenerator().render(
        single_host_specification(enabled=True, host_port_base=49300)
    )

    compose = files[PurePosixPath("deploy", "single-host", "compose.override.yml")]
    environment = files[PurePosixPath("deploy", "single-host", "runtime.env.example")]

    assert 'PUBLIC_HTTP_PORT:-49300' in compose
    assert 'PUBLIC_HTTP_PORT=49300' in environment
    assert "public application proxy | `49300`" in files[
        PurePosixPath("deploy", "single-host", "README.md")
    ]


def test_render_adds_windows_bootstrap_only_when_selected() -> None:
    files = SingleHostOperatingGenerator().render(
        single_host_specification(enabled=True, bootstrap_provider="windows_task_scheduler")
    )

    bootstrap = files[PurePosixPath("deploy", "single-host", "windows", "start-compose.ps1")]

    assert "docker compose" in bootstrap
    assert "Docker engine did not become ready" in bootstrap
    assert "config --format json" in bootstrap
    assert "Published host port collision" in bootstrap
    assert "up -d --wait" in bootstrap
    assert 'COMPOSE_IGNORE_ORPHANS = "true"' in bootstrap
    assert "runtime.env" in bootstrap


def test_single_host_requires_local_application_environment() -> None:
    with pytest.raises(
        ValidationError, match="requires tooling.local_environment.enabled"
    ):
        ToolingSpec(single_host=SingleHostSpec(enabled=True))

    with pytest.raises(ValidationError, match="requires local_environment.application_enabled"):
        ToolingSpec(
            local_environment=LocalEnvironmentSpec(enabled=True),
            single_host=SingleHostSpec(enabled=True),
        )


def test_plan_marks_single_host_files_generated_and_plugin_is_registered() -> None:
    specification = single_host_specification(enabled=True)
    generator = SingleHostOperatingGenerator()
    rendered = generator.render(specification)

    plan = generator.plan(specification)
    plugin = create_fastapi_generator_plugins("kis_auto_trading").project.get(
        SINGLE_HOST_GENERATOR_ID
    )

    assert plugin.render(specification) == rendered
    for planned_file in plan.files:
        assert planned_file.ownership is FileOwnership.GENERATED
        assert planned_file.expected_content_hash == content_hash(
            rendered[planned_file.relative_path]
        )
