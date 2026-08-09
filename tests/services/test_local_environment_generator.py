from pathlib import PurePosixPath

import pytest

from autoforge.core.generation import FileOwnership, Generator, content_hash
from autoforge.core.specification import (
    ApplicationSpec,
    DatabaseShardSpec,
    DatabaseStoreSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
)
from autoforge.services.generation.local_environment import LocalEnvironmentGenerator


def integration_specification(*, enabled: bool = False) -> ProjectSpec:
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
                ),
                DatabaseStoreSpec(
                    name="automation", global_url_env="AUTOMATION_DATABASE_URL"
                ),
                DatabaseStoreSpec(
                    name="account",
                    shards=[
                        DatabaseShardSpec(
                            shard_id="1", url_env="ACCOUNT_SHARD_1_DATABASE_URL"
                        ),
                        DatabaseShardSpec(
                            shard_id="2", url_env="ACCOUNT_SHARD_2_DATABASE_URL"
                        ),
                    ],
                ),
            ],
            services=[
                ServiceSpec(
                    name="session",
                    kind="redis_session",
                    namespace="kis_session",
                    ttl_seconds=3600,
                    mode="cluster",
                ),
                ServiceSpec(
                    name="events",
                    kind="rabbitmq",
                    outbox_stores=["automation"],
                ),
            ],
        ),
        tooling={"local_environment": {"enabled": enabled}},
    )


def test_local_environment_generator_satisfies_protocol() -> None:
    generator: Generator[ProjectSpec] = LocalEnvironmentGenerator()

    assert isinstance(generator, Generator)


def test_render_is_empty_until_enabled() -> None:
    assert LocalEnvironmentGenerator().render(integration_specification()) == {}


def test_render_creates_disposable_kis_integration_services() -> None:
    files = LocalEnvironmentGenerator().render(integration_specification(enabled=True))

    assert set(files) == {
        PurePosixPath("environment", "compose.integration.yml"),
        PurePosixPath("environment", ".env.example"),
        PurePosixPath("environment", "README.md"),
        PurePosixPath("environment", "postgres-init", "00-databases.sql"),
    }
    compose = files[PurePosixPath("environment", "compose.integration.yml")]
    environment = files[PurePosixPath("environment", ".env.example")]
    databases = files[
        PurePosixPath("environment", "postgres-init", "00-databases.sql")
    ]

    assert "image: postgres:16-alpine" in compose
    assert "redis-7000:" in compose
    assert "redis-7001:" in compose
    assert "redis-7002:" in compose
    assert "redis-cluster-init" in compose
    assert "rabbitmq:4.1-management-alpine" in compose
    assert "CREATE DATABASE \"identity\";" in databases
    assert "CREATE DATABASE \"automation\";" in databases
    assert "CREATE DATABASE \"account_shard_1\";" in databases
    assert "CREATE DATABASE \"account_shard_2\";" in databases
    assert "REDIS_CLUSTER_URL=redis://redis-7000:7000" in environment
    assert "POSTGRES_PORT=25432" in environment
    assert "RABBITMQ_AMQP_PORT=25672" in environment
    assert "RABBITMQ_URL=amqp://autoforge:change-me@rabbitmq:5672/" in environment


def test_plan_marks_environment_files_generated() -> None:
    generator = LocalEnvironmentGenerator()
    specification = integration_specification(enabled=True)
    rendered = generator.render(specification)

    plan = generator.plan(specification)

    assert len(plan.files) == len(rendered)
    for planned_file in plan.files:
        assert planned_file.ownership is FileOwnership.GENERATED
        assert planned_file.expected_content_hash == content_hash(
            rendered[planned_file.relative_path]
        )


def test_sentinel_is_not_silently_rendered_as_standalone() -> None:
    specification = integration_specification(enabled=True)
    sentinel = specification.application.services[0].model_copy(
        update={"mode": "sentinel"}
    )
    application = specification.application.model_copy(
        update={"services": [sentinel, specification.application.services[1]]}
    )

    with pytest.raises(ValueError, match="does not yet support Redis Sentinel"):
        LocalEnvironmentGenerator().render(
            specification.model_copy(update={"application": application})
        )
