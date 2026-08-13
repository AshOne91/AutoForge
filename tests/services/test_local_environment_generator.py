from pathlib import PurePosixPath

import pytest
import yaml

from autoforge.core.generation import FileOwnership, Generator, content_hash
from autoforge.core.specification import (
    ApplicationSpec,
    DatabaseShardSpec,
    DatabaseStoreSpec,
    DurableJobSpec,
    ProjectInfo,
    ProjectSpec,
    ServiceSpec,
)
from autoforge.services.generation.local_environment import LocalEnvironmentGenerator


def integration_specification(
    *,
    enabled: bool = False,
    durable_jobs: bool = False,
    application: bool = False,
    rag: bool = False,
    rag_search_backend: str = "elasticsearch",
    host_port_base: int | None = None,
    durable_job_worker_restart_policy: str = "unless-stopped",
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
            durable_jobs=[
                DurableJobSpec(
                    name="news_collection",
                    store="automation",
                    event_type="news.collection.requested",
                    routing_key="news.collection.requested",
                    schedule="0 * * * *",
                )
            ]
            if durable_jobs
            else [],
            durable_job_worker_restart_policy=durable_job_worker_restart_policy,
        ),
        tooling={
            "local_environment": {
                "enabled": enabled,
                "application_enabled": application,
                "host_port_base": host_port_base,
            },
            "rag": {"enabled": rag, "search_backend": rag_search_backend},
        },
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
    assert "- |-\n        if redis-cli" in compose
    assert "cluster nodes | grep -q '[0-9]-[0-9]'" in compose
    assert "existing Redis cluster did not become healthy" in compose
    assert "redis-7002:7002 --cluster-replicas 0 --cluster-yes" in compose
    assert "rabbitmq:4.1-management-alpine" in compose
    assert "CREATE DATABASE \"identity\";" in databases
    assert "CREATE DATABASE \"automation\";" in databases
    assert "CREATE DATABASE \"account_shard_1\";" in databases
    assert "CREATE DATABASE \"account_shard_2\";" in databases
    assert "REDIS_CLUSTER_URL=redis://redis-7000:7000" in environment
    assert "POSTGRES_PORT=25432" in environment
    assert "RABBITMQ_AMQP_PORT=25672" in environment
    assert "RABBITMQ_URL=amqp://autoforge:change-me@rabbitmq:5672/" in environment
    assert "LOCAL_BIND_ADDRESS=127.0.0.1" in environment
    assert '"${LOCAL_BIND_ADDRESS:-127.0.0.1}:${POSTGRES_PORT:-25432}:5432"' in compose


def test_render_connects_rag_consumers_to_the_shared_network() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(enabled=True, durable_jobs=True, application=True, rag=True)
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    environment = files[PurePosixPath("environment", ".env.example")]

    assert compose["networks"]["rag"] == {
        "name": "${RAG_NETWORK_NAME:-kis_auto_trading-rag}",
        "external": True,
    }
    assert compose["services"]["application"]["networks"] == ["default", "rag"]
    assert compose["services"]["durable-job-worker"]["networks"] == [
        "default",
        "rag",
    ]
    assert compose["services"]["durable-job-worker"]["restart"] == "unless-stopped"
    assert "RAG_NETWORK_NAME=kis_auto_trading-rag" in environment
    assert "RAG_SEARCH_BACKEND=elasticsearch" in environment
    assert "RAG_SEARCH_URL=http://elasticsearch:9200" in environment
    assert "RAG_OLLAMA_URL=http://ollama:11434" in environment
    assert "RAG_EMBEDDING_MODEL=embeddinggemma" in environment


def test_render_configures_rag_consumers_for_opensearch() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            durable_jobs=True,
            application=True,
            rag=True,
            rag_search_backend="opensearch",
        )
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    environment = files[PurePosixPath("environment", ".env.example")]

    assert (
        compose["services"]["application"]["environment"]["RAG_SEARCH_BACKEND"]
        == "${RAG_SEARCH_BACKEND:-opensearch}"
    )
    assert (
        compose["services"]["durable-job-worker"]["environment"]["RAG_SEARCH_URL"]
        == "${RAG_SEARCH_URL:-http://opensearch:9200}"
    )
    assert "RAG_SEARCH_BACKEND=opensearch" in environment
    assert "RAG_SEARCH_URL=http://opensearch:9200" in environment


def test_render_adds_airflow_for_durable_jobs() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(enabled=True, durable_jobs=True)
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    environment = files[PurePosixPath("environment", ".env.example")]
    databases = files[
        PurePosixPath("environment", "postgres-init", "00-databases.sql")
    ]
    readme = files[PurePosixPath("environment", "README.md")]

    airflow = compose["services"]
    assert {"airflow-init", "airflow-webserver", "airflow-scheduler"} <= set(airflow)
    assert airflow["airflow-init"]["command"] == ["airflow", "db", "migrate"]
    assert airflow["airflow-webserver"]["command"] == "webserver"
    assert airflow["airflow-scheduler"]["command"] == "scheduler"
    assert airflow["airflow-webserver"]["environment"]["DURABLE_JOB_API_TOKEN"] == "${DURABLE_JOB_API_TOKEN:?set DURABLE_JOB_API_TOKEN}"
    assert "../airflow/dags:/opt/airflow/dags:ro" in airflow["airflow-scheduler"]["volumes"]
    assert "airflow-home:/opt/airflow" in airflow["airflow-init"]["volumes"]
    assert "DURABLE_JOB_API_TOKEN=change-me" in environment
    assert 'CREATE DATABASE "airflow";' in databases
    assert "Airflow" in readme


def test_render_starts_application_without_durable_jobs() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(enabled=True, application=True)
    )

    compose = files[PurePosixPath("environment", "compose.integration.yml")]
    environment = files[PurePosixPath("environment", ".env.example")]
    readme = files[PurePosixPath("environment", "README.md")]

    assert "  migrate:" in compose
    assert "  application:" in compose
    assert "  airflow:" not in compose
    assert "  outbox-relay:" not in compose
    assert "  durable-job-worker:" not in compose
    assert "DURABLE_JOB_API_TOKEN:" not in compose
    assert "DURABLE_JOB_API_TOKEN=" not in environment
    assert "APPLICATION_PORT=28000" in environment
    assert "The generated application is built from Dockerfile." in readme
    assert "AWS Launch Template UserData is a separate deployment concern" in readme


def test_render_connects_docker_application_to_airflow() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(enabled=True, durable_jobs=True, application=True)
    )

    compose = files[PurePosixPath("environment", "compose.integration.yml")]
    environment = files[PurePosixPath("environment", ".env.example")]
    readme = files[PurePosixPath("environment", "README.md")]

    assert "  migrate:" in compose
    assert "command: [\"python\", \"scripts/migrate.py\"]" in compose
    assert "  application:" in compose
    assert "pull_policy: never" in compose
    assert "  outbox-relay:" in compose
    assert "command: [\"python\", \"scripts/run_outbox_relay.py\"]" in compose
    assert "  durable-job-worker:" in compose
    assert "command: [\"python\", \"scripts/run_durable_job_worker.py\"]" in compose
    assert "condition: service_completed_successfully" in compose
    assert "DURABLE_JOB_API_URL: ${DURABLE_JOB_API_URL:-http://application:8000}" in compose
    assert "DURABLE_JOB_API_TOKEN: ${DURABLE_JOB_API_TOKEN:?set DURABLE_JOB_API_TOKEN}" in compose
    assert "APPLICATION_PORT=28000" in environment
    assert "DURABLE_JOB_API_URL=http://application:8000" in environment
    assert "migrations run before the generated application starts" in readme


def test_render_marks_runtime_services_restartable() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(enabled=True, durable_jobs=True, application=True)
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    services = compose["services"]

    for service_name in (
        "postgres",
        "redis-7000",
        "redis-7001",
        "redis-7002",
        "rabbitmq",
        "application",
        "outbox-relay",
        "durable-job-worker",
        "airflow-webserver",
        "airflow-scheduler",
    ):
        assert services[service_name]["restart"] == "unless-stopped"

    assert services["migrate"]["restart"] == "no"
    assert services["redis-cluster-init"]["restart"] == "no"
    assert services["airflow-init"].get("restart") is None
    assert services["durable-job-worker"]["healthcheck"]["test"] == [
        "CMD",
        "python",
        "-c",
        "import asyncio, os, aio_pika; connection = asyncio.run(aio_pika.connect(os.environ['RABBITMQ_URL'], timeout=2)); asyncio.run(connection.close())",
    ]
    assert services["outbox-relay"]["healthcheck"]["test"] == services[
        "durable-job-worker"
    ]["healthcheck"]["test"]


def test_render_uses_durable_worker_restart_policy_from_specification() -> None:
    specification = integration_specification(
        enabled=True,
        durable_jobs=True,
        application=True,
        durable_job_worker_restart_policy="on-failure",
    )

    compose = yaml.safe_load(LocalEnvironmentGenerator().render(specification)[
        PurePosixPath("environment/compose.integration.yml")
    ])

    assert compose["services"]["durable-job-worker"]["restart"] == "on-failure"


def test_render_uses_the_declared_local_host_port_block() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            durable_jobs=True,
            application=True,
            host_port_base=49300,
        )
    )

    compose = files[PurePosixPath("environment", "compose.integration.yml")]
    environment = files[PurePosixPath("environment", ".env.example")]

    assert "APPLICATION_PORT=49300" in environment
    assert "POSTGRES_PORT=49310" in environment
    assert "RABBITMQ_AMQP_PORT=49330" in environment
    assert "RABBITMQ_MANAGEMENT_PORT=49331" in environment
    assert "AIRFLOW_PORT=49340" in environment
    assert '"${LOCAL_BIND_ADDRESS:-127.0.0.1}:${AIRFLOW_PORT:-49340}:8080"' in compose


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
