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
    postgres_mode: str = "standalone",
    database_provider: str = "postgresql",
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
                "database_provider": database_provider,
                "postgres_mode": postgres_mode,
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
    for port in range(7000, 7006):
        assert f"redis-{port}:" in compose
        assert f"redis-{port}-data:/data" in compose
        assert f"- redis-{port}\n      - --cluster-preferred-endpoint-type" in compose
    assert "- --cluster-announce-hostname" in compose
    assert "- hostname" in compose
    assert "redis-cluster-init" in compose
    assert "for port in 7001 7002 7003 7004 7005; do" in compose
    assert "set -- $$(getent hosts redis-$$port)" in compose
    assert 'cluster meet "$$1" "$$port"' in compose
    assert "- |-\n        if redis-cli" in compose
    assert "cluster nodes | grep -q '[0-9]-[0-9]'" in compose
    assert "existing Redis cluster did not meet the 3-primary/3-replica topology" in compose
    assert "redis-7005:7005 --cluster-replicas 1 --cluster-yes" in compose
    assert "$$topology" in compose
    assert "rabbitmq:4.1-management-alpine" in compose
    assert "CREATE DATABASE %I" in databases
    assert "('identity')" in databases
    assert "('automation')" in databases
    assert "('account_shard_1')" in databases
    assert "('account_shard_2')" in databases
    assert "REDIS_CLUSTER_URL=redis://redis-7000:7000" in environment
    assert "REDIS_CLUSTER_STARTUP_NODES=redis://redis-7000:7000,redis://redis-7001:7001,redis://redis-7002:7002,redis://redis-7003:7003,redis://redis-7004:7004,redis://redis-7005:7005" in environment
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
    assert "('airflow')" in databases
    assert "Airflow" in readme


def test_render_creates_postgresql_ha_environment() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            durable_jobs=True,
            application=True,
            postgres_mode="ha",
        )
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    environment = files[PurePosixPath("environment", ".env.example")]
    haproxy_config = files[PurePosixPath("environment", "postgres-ha", "haproxy.cfg")]
    services = compose["services"]

    assert {f"etcd-{index}" for index in range(3)} <= set(services)
    assert {f"postgres-ha-{index}" for index in range(3)} <= set(services)
    assert services["postgres"]["image"] == "haproxy:3.0-alpine"
    assert services["etcd-0"]["healthcheck"]["test"] == [
        "CMD",
        "/usr/local/bin/etcdctl",
        "endpoint",
        "health",
    ]
    assert services["postgres-ha-0"]["depends_on"] == {
        "etcd-0": {"condition": "service_healthy"},
        "etcd-1": {"condition": "service_healthy"},
        "etcd-2": {"condition": "service_healthy"},
    }
    assert services["postgres-ha-1"]["depends_on"]["postgres-ha-0"] == {
        "condition": "service_healthy"
    }
    assert services["postgres-ha-2"]["depends_on"]["postgres-ha-1"] == {
        "condition": "service_healthy"
    }
    assert services["postgres-ha-init"]["restart"] == "no"
    assert "PGUSER_SUPERUSER" not in services["postgres-ha-0"]["environment"]
    assert services["postgres-ha-init"]["environment"]["POSTGRES_SUPERUSER"] == "postgres"
    assert services["postgres-ha-init"]["environment"]["POSTGRES_PASSWORD"] == "${POSTGRES_PASSWORD:-change-me}"
    assert "CREATE ROLE %I LOGIN" in services["postgres-ha-init"]["command"][2]
    assert "ALTER DATABASE %I OWNER TO %I" in services["postgres-ha-init"]["command"][2]
    assert services["migrate"]["depends_on"] == {
        "postgres-ha-init": {"condition": "service_completed_successfully"}
    }
    assert services["airflow-init"]["depends_on"] == {
        "postgres-ha-init": {"condition": "service_completed_successfully"}
    }
    assert services["postgres-ha-0"]["environment"]["SPILO_CONFIGURATION"].count(
        "synchronous_mode: true"
    ) == 1
    assert "POSTGRES_REPLICATION_PASSWORD=change-me-replication" in environment
    assert "GET /primary" in haproxy_config


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
        "redis-7003",
        "redis-7004",
        "redis-7005",
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
    assert services["application"]["healthcheck"]["test"] == [
        "CMD",
        "python",
        "-c",
        "from urllib.request import urlopen; import socket; import asyncio, os; from urllib.parse import urlparse; from redis.cluster import ClusterNode; from redis.asyncio.cluster import RedisCluster; urlopen('http://127.0.0.1:8000/health').read(); [socket.create_connection(target, 2).close() for target in [('postgres', 5432)]]; startup_nodes=[ClusterNode(urlparse(value).hostname, urlparse(value).port or 6379) for value in os.environ['REDIS_CLUSTER_STARTUP_NODES'].split(',')]; client=RedisCluster.from_url(os.environ['REDIS_CLUSTER_URL'], startup_nodes=startup_nodes, decode_responses=True, require_full_coverage=True); asyncio.run(client.ping())",
    ]


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
