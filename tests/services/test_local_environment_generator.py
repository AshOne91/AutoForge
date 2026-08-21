import json
import os
import uuid
from pathlib import Path, PurePosixPath

import anyio
import pytest
import yaml

from autoforge.core.generation import FileOwnership, Generator, content_hash
from autoforge.core.specification import (
    ApplicationCompositionSpec,
    ApplicationSpec,
    ControlPlaneHeartbeatSpec,
    DatabaseShardSpec,
    DatabaseStoreSpec,
    DistributedLockSpec,
    DurableJobSpec,
    KeyValueStoreSpec,
    LocalApplicationCompositionSpec,
    ProjectInfo,
    ProjectSpec,
    RuntimeEnvironmentSpec,
    RuntimeEnvironmentTarget,
    ServiceSpec,
    ServiceTokenSpec,
)
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation.fastapi_project import FastAPIProjectGenerator
from autoforge.services.generation.key_value_store import KeyValueStoreGenerator
from autoforge.services.generation.local_environment import LocalEnvironmentGenerator


def integration_specification(
    *,
    enabled: bool = False,
    durable_jobs: bool = False,
    application: bool = False,
    rag: bool = False,
    rag_search_backend: str = "elasticsearch",
    rag_search_mode: str = "standalone",
    postgres_mode: str = "standalone",
    mysql_mode: str = "standalone",
    database_provider: str = "postgresql",
    include_rabbitmq: bool = True,
    rabbitmq_mode: str = "standalone",
    rabbitmq_queue_type: str = "classic",
    airflow_scheduler_replicas: int = 1,
    host_port_base: int | None = None,
    durable_job_worker_restart_policy: str = "unless-stopped",
    heartbeat_reporter: bool = False,
    key_value_store_backend: str | None = None,
    key_value_store_mode: str = "standalone",
    realtime_backplane: str = "none",
    modules: list[str] | None = None,
    compositions: list[ApplicationCompositionSpec] | None = None,
    local_application_compositions: list[LocalApplicationCompositionSpec] | None = None,
) -> ProjectSpec:
    tooling = {
        "local_environment": {
            "enabled": enabled,
            "application_enabled": application,
            "database_provider": database_provider,
            "postgres_mode": postgres_mode,
            "mysql_mode": mysql_mode,
            "rabbitmq_mode": rabbitmq_mode,
            "airflow_scheduler_replicas": airflow_scheduler_replicas,
            "host_port_base": host_port_base,
            "application_compositions": [
                composition.model_dump()
                for composition in local_application_compositions or []
            ],
        },
        "rag": {
            "enabled": rag,
            "search_backend": rag_search_backend,
            "search_mode": rag_search_mode,
        },
        "realtime": {
            "enabled": realtime_backplane != "none",
            "backplane": realtime_backplane,
        },
    }
    if key_value_store_backend is not None:
        tooling["key_value_store"] = {
            "enabled": True,
            "backend": key_value_store_backend,
            "mode": key_value_store_mode,
        }
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(
            modules=modules or [],
            compositions=compositions or [],
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
                *(
                    [
                        ServiceSpec(
                            name="events",
                            kind="rabbitmq",
                            queue_type=rabbitmq_queue_type,
                            outbox_stores=["automation"],
                        )
                    ]
                    if include_rabbitmq
                    else []
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
            control_plane_heartbeat=ControlPlaneHeartbeatSpec(
                enabled=heartbeat_reporter
            ),
        ),
        tooling=tooling,
    )


def test_local_environment_generator_satisfies_protocol() -> None:
    generator: Generator[ProjectSpec] = LocalEnvironmentGenerator()

    assert isinstance(generator, Generator)


def test_runtime_environments_flow_to_application_compose_and_example() -> None:
    specification = integration_specification(enabled=True, application=True)
    application = specification.application.model_copy(
        update={
            "runtime_environments": [
                RuntimeEnvironmentSpec(name="KIS_APP_KEY"),
                RuntimeEnvironmentSpec(name="KIS_TOKEN_SCOPE", required=False),
            ]
        }
    )

    files = LocalEnvironmentGenerator().render(
        specification.model_copy(update={"application": application})
    )
    compose = yaml.safe_load(files[PurePosixPath("environment/compose.integration.yml")])
    environment = files[PurePosixPath("environment/.env.example")]

    application_environment = compose["services"]["application"]["environment"]
    assert application_environment["KIS_APP_KEY"] == "${KIS_APP_KEY:?set KIS_APP_KEY}"
    assert application_environment["KIS_TOKEN_SCOPE"] == "${KIS_TOKEN_SCOPE:-}"
    assert "KIS_APP_KEY=\n" in environment
    assert "KIS_TOKEN_SCOPE=\n" in environment


def test_named_application_composition_generates_local_compose_service() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            application=True,
            host_port_base=49400,
            modules=["identity", "signal"],
            compositions=[
                ApplicationCompositionSpec(name="signal_api", modules=["signal"])
            ],
            local_application_compositions=[
                LocalApplicationCompositionSpec(
                    name="signal_api",
                    host_port_offset=1,
                )
            ],
        )
    )

    compose = yaml.safe_load(files[PurePosixPath("environment/compose.integration.yml")])
    service = compose["services"]["application-signal-api"]
    composition = json.loads(
        files[PurePosixPath("environment/service-composition.json")]
    )

    assert service["command"] == [
        "python",
        "-m",
        "uvicorn",
        "kis_auto_trading.application.compositions.signal_api:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    assert service["ports"] == [
        "${LOCAL_BIND_ADDRESS:-127.0.0.1}:${SIGNAL_API_PORT:-49401}:8000"
    ]
    assert service["environment"]["LOG_DIRECTORY"] == "/app/logs/application-signal-api"
    assert "SIGNAL_API_PORT=49401\n" in files[PurePosixPath("environment/.env.example")]
    assert next(
        entry
        for entry in composition["services"]
        if entry["name"] == "application-signal-api"
    )["role"] == "api"


def test_runtime_environments_only_flow_to_declared_compose_targets() -> None:
    specification = integration_specification(
        enabled=True, application=True, durable_jobs=True
    )
    application = specification.application.model_copy(
        update={
            "runtime_environments": [
                RuntimeEnvironmentSpec(name="API_ONLY"),
                RuntimeEnvironmentSpec(
                    name="WORKER_ONLY",
                    targets=[RuntimeEnvironmentTarget.DURABLE_JOB_WORKER],
                ),
                RuntimeEnvironmentSpec(
                    name="SHARED_RUNTIME",
                    targets=[
                        RuntimeEnvironmentTarget.APPLICATION,
                        RuntimeEnvironmentTarget.DURABLE_JOB_WORKER,
                    ],
                ),
            ]
        }
    )

    files = LocalEnvironmentGenerator().render(
        specification.model_copy(update={"application": application})
    )
    compose = yaml.safe_load(files[PurePosixPath("environment/compose.integration.yml")])

    assert set(compose["services"]["application"]["environment"]) >= {
        "API_ONLY",
        "SHARED_RUNTIME",
    }
    assert "WORKER_ONLY" not in compose["services"]["application"]["environment"]
    assert set(compose["services"]["durable-job-worker"]["environment"]) >= {
        "WORKER_ONLY",
        "SHARED_RUNTIME",
    }
    assert "API_ONLY" not in compose["services"]["durable-job-worker"]["environment"]


def test_render_is_empty_until_enabled() -> None:
    assert LocalEnvironmentGenerator().render(integration_specification()) == {}


def test_render_creates_service_composition_from_generated_compose() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            application=True,
            durable_jobs=True,
            postgres_mode="ha",
            rabbitmq_mode="cluster",
            rabbitmq_queue_type="quorum",
        )
    )

    composition = json.loads(files[PurePosixPath("environment/service-composition.json")])
    services = {service["name"]: service for service in composition["services"]}
    declared = {
        service["name"]: service
        for service in composition["declared_service_contracts"]
    }

    assert composition["compose_file"] == "environment/compose.integration.yml"
    assert services["migrate"]["lifecycle"] == "one_shot"
    assert services["migrate"]["dependencies"] == {
        "postgres-ha-init": "service_completed_successfully"
    }
    assert services["application"]["healthcheck"] is True
    assert services["application"]["role"] == "api"
    assert services["application"]["restart_policy"] == "unless-stopped"
    assert services["outbox-relay"]["role"] == "relay"
    assert services["durable-job-worker"]["role"] == "worker"
    assert services["airflow-scheduler"]["role"] == "scheduler"
    assert "RABBITMQ_URL" in services["outbox-relay"]["configuration_env"]
    assert declared["session"]["configuration_env"] == [
        "REDIS_CLUSTER_URL",
        "REDIS_CLUSTER_STARTUP_NODES",
    ]
    assert declared["events"]["event_queue"]["queue_type"] == "quorum"
    assert composition["durable_jobs"] == [
        {
            "event_type": "news.collection.requested",
            "name": "news_collection",
            "routing_key": "news.collection.requested",
            "schedule": "0 * * * *",
            "store": "automation",
        }
    ]


def test_application_composition_passes_opt_in_heartbeat_environment() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            application=True,
            heartbeat_reporter=True,
        )
    )
    compose = yaml.safe_load(files[PurePosixPath("environment/compose.integration.yml")])
    environment = files[PurePosixPath("environment/.env.example")]

    application_environment = compose["services"]["application"]["environment"]
    assert application_environment["CONTROL_PLANE_HEARTBEAT_URL"] == (
        "${CONTROL_PLANE_HEARTBEAT_URL:-}"
    )
    assert application_environment["CONTROL_PLANE_API_TOKEN"] == (
        "${CONTROL_PLANE_API_TOKEN:-}"
    )
    assert "CONTROL_PLANE_HEARTBEAT_URL=\n" in environment
    assert "CONTROL_PLANE_API_TOKEN=\n" in environment


def test_render_creates_mysql_standalone_environment() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            application=True,
            database_provider="mysql",
            include_rabbitmq=False,
        )
    )

    compose = yaml.safe_load(files[PurePosixPath("environment/compose.integration.yml")])
    environment = files[PurePosixPath("environment/.env.example")]

    assert "mysql" in compose["services"]
    assert "mysql-init" in compose["services"]
    assert "postgres" not in compose["services"]
    assert "mysql-data" in compose["volumes"]
    assert compose["services"]["migrate"]["depends_on"] == {
        "mysql-init": {"condition": "service_completed_successfully"}
    }
    assert "mysql+asyncmy://${MYSQL_USER:-autoforge}" in compose["services"]["application"]["environment"]["IDENTITY_DATABASE_URL"]
    assert "MYSQL_ROOT_PASSWORD=change-me-root" in environment
    assert "MYSQL_PORT=23306" in environment
    assert "CREATE USER IF NOT EXISTS '$$MYSQL_USER'@'%'" in compose["services"]["mysql-init"]["command"][-1]
    assert "GRANT ALL PRIVILEGES ON identity.*" in compose["services"]["mysql-init"]["command"][-1]
    assert "up -d --wait" not in files[PurePosixPath("environment/README.md")]
    assert "mysql-init" in files[PurePosixPath("environment/README.md")]


def test_mysql_runtime_rejects_postgresql_only_profiles() -> None:
    with pytest.raises(ValueError, match="PostgreSQL-specific messaging"):
        integration_specification(
            database_provider="mysql",
            durable_jobs=True,
        )

    with pytest.raises(ValueError, match="database_provider=mysql"):
        integration_specification(mysql_mode="ha")


def test_render_creates_mysql_ha_environment() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            application=True,
            database_provider="mysql",
            mysql_mode="ha",
            include_rabbitmq=False,
        )
    )

    compose = yaml.safe_load(files[PurePosixPath("environment/compose.integration.yml")])
    environment = files[PurePosixPath("environment/.env.example")]

    assert {f"mysql-ha-{index}" for index in range(3)} <= set(compose["services"])
    assert "mysql-router-bootstrap" in compose["services"]
    assert compose["services"]["mysql"]["ports"] == [
        "${LOCAL_BIND_ADDRESS:-127.0.0.1}:${MYSQL_PORT:-23306}:6446"
    ]
    assert compose["services"]["mysql-init"]["depends_on"] == {
        "mysql": {"condition": "service_healthy"}
    }
    assert "mysql -hmysql -P 6446" in compose["services"]["mysql-init"]["command"][-1]
    assert compose["services"]["mysql-init"]["environment"]["MYSQL_PASSWORD"] == "${MYSQL_PASSWORD:-change-me}"
    assert compose["services"]["mysql"]["depends_on"] == {
        "mysql-router-bootstrap": {"condition": "service_completed_successfully"}
    }
    assert "@mysql:6446/identity?charset=utf8mb4" in compose["services"]["application"]["environment"]["IDENTITY_DATABASE_URL"]
    assert "/readiness" in compose["services"]["application"]["healthcheck"]["test"][-1]
    assert "mysql-router-data" in compose["volumes"]
    assert "MYSQL_CLUSTER_ADMIN_PASSWORD=change-me-cluster" in environment
    assert compose["services"]["mysql"]["build"]["args"] == {
        "MYSQL_ROUTER_VERSION": "${MYSQL_ROUTER_VERSION:-8.4.8}"
    }
    assert PurePosixPath("environment/mysql-ha/Dockerfile.router") in files
    assert "dba.getCluster" in files[PurePosixPath("environment/mysql-ha/bootstrap.js")]

    with pytest.raises(ValueError, match="postgres_mode=standalone"):
        integration_specification(
            database_provider="mysql",
            postgres_mode="ha",
            include_rabbitmq=False,
        )


def test_render_creates_disposable_kis_integration_services() -> None:
    files = LocalEnvironmentGenerator().render(integration_specification(enabled=True))

    assert set(files) == {
        PurePosixPath("environment", "compose.integration.yml"),
        PurePosixPath("environment", "service-composition.json"),
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
    assert "- rabbitmq-data:/var/lib/rabbitmq" in compose
    assert "  rabbitmq-data:" in compose
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


def test_render_connects_memcached_key_value_store_to_application() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            application=True,
            durable_jobs=True,
            key_value_store_backend="memcached",
        )
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    environment = files[PurePosixPath("environment", ".env.example")]
    readme = files[PurePosixPath("environment", "README.md")]
    composition = json.loads(
        files[PurePosixPath("environment", "service-composition.json")]
    )

    assert compose["services"]["memcached"] == {
        "image": "memcached:1.6-alpine",
        "restart": "unless-stopped",
        "healthcheck": {
            "test": ["CMD-SHELL", "nc -z 127.0.0.1 11211"],
            "interval": "3s",
            "timeout": "3s",
            "retries": 20,
        },
    }
    application = compose["services"]["application"]
    assert application["environment"]["MEMCACHED_HOST"] == "${MEMCACHED_HOST:-memcached}"
    assert application["environment"]["MEMCACHED_PORT"] == "${MEMCACHED_PORT:-11211}"
    assert application["depends_on"]["memcached"] == {
        "condition": "service_healthy"
    }
    worker = compose["services"]["durable-job-worker"]
    assert worker["environment"]["MEMCACHED_HOST"] == "${MEMCACHED_HOST:-memcached}"
    assert worker["depends_on"]["memcached"] == {"condition": "service_healthy"}
    assert "MEMCACHED_HOST=memcached" in environment
    assert "MEMCACHED_PORT=11211" in environment
    assert "Memcached is reachable only through Compose service DNS" in readme
    memcached = next(
        service for service in composition["services"] if service["name"] == "memcached"
    )
    assert memcached["role"] == "infrastructure"
    assert memcached["healthcheck"] is True
    assert memcached["published_ports"] == []


def test_render_injects_each_selected_redis_runtime_contract() -> None:
    specification = integration_specification(
        enabled=True,
        application=True,
        key_value_store_backend="redis",
        key_value_store_mode="cluster",
    )
    key_value_store = KeyValueStoreSpec(
        enabled=True,
        backend="redis",
        mode="cluster",
        cluster_url_environment="CACHE_CLUSTER_URL",
        cluster_startup_nodes_environment="CACHE_CLUSTER_NODES",
    )
    distributed_lock = DistributedLockSpec(
        enabled=True,
        mode="cluster",
        cluster_url_environment="LOCK_CLUSTER_URL",
        cluster_startup_nodes_environment="LOCK_CLUSTER_NODES",
    )
    tooling = specification.tooling.model_copy(
        update={
            "distributed_lock": distributed_lock,
            "key_value_store": key_value_store,
        }
    )
    files = LocalEnvironmentGenerator().render(
        specification.model_copy(update={"tooling": tooling})
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    environment = files[PurePosixPath("environment", ".env.example")]

    application_environment = compose["services"]["application"]["environment"]
    assert application_environment["REDIS_CLUSTER_URL"] == (
        "${REDIS_CLUSTER_URL:-redis://redis-7000:7000}"
    )
    assert application_environment["CACHE_CLUSTER_URL"] == (
        "${CACHE_CLUSTER_URL:-redis://redis-7000:7000}"
    )
    assert application_environment["LOCK_CLUSTER_URL"] == (
        "${LOCK_CLUSTER_URL:-redis://redis-7000:7000}"
    )
    assert "CACHE_CLUSTER_NODES=redis://redis-7000:7000" in environment
    assert "LOCK_CLUSTER_NODES=redis://redis-7000:7000" in environment


def test_render_rejects_conflicting_redis_runtime_modes() -> None:
    with pytest.raises(ValueError, match="one shared Redis mode"):
        LocalEnvironmentGenerator().render(
            integration_specification(
                enabled=True,
                key_value_store_backend="redis",
                key_value_store_mode="standalone",
            )
        )


@pytest.mark.integration
@pytest.mark.anyio
async def test_generated_memcached_adapter_recovers_after_process_restart(
    tmp_path: Path,
) -> None:
    if os.environ.get("AUTOFORGE_DOCKER_MEMCACHED_INTEGRATION") != "1":
        pytest.skip("set AUTOFORGE_DOCKER_MEMCACHED_INTEGRATION=1 to run Docker")

    package_name = f"memcached_profile_{uuid.uuid4().hex}"
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Memcached Profile",
            package_name=package_name,
            version="0.1.0",
        ),
        application=ApplicationSpec(),
        tooling={
            "local_environment": {"enabled": True},
            "key_value_store": {"enabled": True, "backend": "memcached"},
        },
    )
    files = LocalEnvironmentGenerator().render(specification)
    for relative_path, content in files.items():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    for generator in (FastAPIProjectGenerator(), KeyValueStoreGenerator()):
        for relative_path, content in generator.render(specification).items():
            target = tmp_path / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    environment = tmp_path / "environment"
    (environment / ".env").write_text(
        files[PurePosixPath("environment", ".env.example")], encoding="utf-8"
    )
    (environment / "compose.memcached-test.yml").write_text(
        "services:\n"
        "  memcached-probe:\n"
        "    image: python:3.12-alpine\n"
        "    working_dir: /workspace\n"
        "    volumes:\n"
        '      - "../:/workspace"\n',
        encoding="utf-8",
    )

    compose = (
        "docker",
        "compose",
        "--env-file",
        "environment/.env",
        "-f",
        "environment/compose.integration.yml",
        "-f",
        "environment/compose.memcached-test.yml",
    )
    probe_code = (
        "import asyncio\n"
        "import socket\n"
        "import sys\n"
        "import types\n"
        "\n"
        "class Client:\n"
        "    def __init__(self, host, port):\n"
        "        self.host = host\n"
        "        self.port = port\n"
        "    def connection(self):\n"
        "        return socket.create_connection((self.host, self.port), timeout=3)\n"
        "    async def version(self):\n"
        "        with self.connection() as connection:\n"
        "            stream = connection.makefile('rwb')\n"
        "            stream.write(b'version\\r\\n')\n"
        "            stream.flush()\n"
        "            return stream.readline().strip()\n"
        "    async def get(self, key):\n"
        "        with self.connection() as connection:\n"
        "            stream = connection.makefile('rwb')\n"
        "            stream.write(b'get ' + key + b'\\r\\n')\n"
        "            stream.flush()\n"
        "            header = stream.readline()\n"
        "            if header == b'END\\r\\n':\n"
        "                return None\n"
        "            size = int(header.split()[3])\n"
        "            value = stream.read(size)\n"
        "            assert stream.read(2) == b'\\r\\n'\n"
        "            assert stream.readline() == b'END\\r\\n'\n"
        "            return value\n"
        "    async def set(self, key, value, *, exptime):\n"
        "        command = (b'set ' + key + b' 0 ' + str(exptime).encode() + b' ' "
        "+ str(len(value)).encode() + b'\\r\\n' + value + b'\\r\\n')\n"
        "        with self.connection() as connection:\n"
        "            stream = connection.makefile('rwb')\n"
        "            stream.write(command)\n"
        "            stream.flush()\n"
        "            return stream.readline() == b'STORED\\r\\n'\n"
        "    async def close(self):\n"
        "        return None\n"
        "\n"
        "sys.modules['aiomcache'] = types.SimpleNamespace(Client=Client)\n"
        "sys.path.insert(0, 'src')\n"
        f"from {package_name}.infrastructure.key_value_store import (\n"
        "    KeyValueStore, KeyValueStoreConfig, MemcachedKeyValueStoreClient,\n"
        ")\n"
        "\n"
        "async def verify():\n"
        "    client = Client(sys.argv[1], int(sys.argv[2]))\n"
        "    config = KeyValueStoreConfig(\n"
        "        memcached_host=sys.argv[1], memcached_port=int(sys.argv[2])\n"
        "    )\n"
        "    store = KeyValueStore(\n"
        "        MemcachedKeyValueStoreClient(config, client=client), 10\n"
        "    )\n"
        "    await store.health_check()\n"
        "    await store.set(sys.argv[3], sys.argv[4])\n"
        "    assert await store.get(sys.argv[3]) == sys.argv[4]\n"
        "\n"
        "asyncio.run(verify())\n"
    )
    runner = AsyncioProcessRunner()
    try:
        result = await runner.run(
            (*compose, "up", "--detach", "--wait", "memcached"),
            cwd=tmp_path,
            timeout_seconds=120,
        )
        assert result.succeeded, result.stderr
        result = await runner.run(
            (
                *compose,
                "run",
                "--rm",
                "--no-deps",
                "memcached-probe",
                "python",
                "-c",
                probe_code,
                "memcached",
                "11211",
                "before",
                "restart",
            ),
            cwd=tmp_path,
            timeout_seconds=30,
        )
        assert result.succeeded, result.stderr
        await anyio.sleep(11)
        result = await runner.run(
            (*compose, "ps", "--quiet", "memcached"),
            cwd=tmp_path,
            timeout_seconds=10,
        )
        assert result.succeeded, result.stderr
        container_id = result.stdout.strip()
        assert container_id
        result = await runner.run(
            ("docker", "inspect", "--format", "{{.RestartCount}}", container_id),
            cwd=tmp_path,
            timeout_seconds=10,
        )
        assert result.succeeded, result.stderr
        initial_restart_count = int(result.stdout.strip())
        result = await runner.run(
            ("docker", "exec", container_id, "kill", "-TERM", "1"),
            cwd=tmp_path,
            timeout_seconds=20,
        )
        assert result.succeeded, result.stderr
        for _ in range(30):
            result = await runner.run(
                (
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Health.Status}} {{.RestartCount}}",
                    container_id,
                ),
                cwd=tmp_path,
                timeout_seconds=10,
            )
            if result.succeeded:
                health, restart_count = result.stdout.strip().split()
                if health == "healthy" and int(restart_count) > initial_restart_count:
                    break
            await anyio.sleep(2)
        else:
            pytest.fail(f"Memcached did not restart: {result.stdout} {result.stderr}")
        for _ in range(15):
            result = await runner.run(
                (
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "memcached-probe",
                    "python",
                    "-c",
                    probe_code,
                    "memcached",
                    "11211",
                    "after",
                    "restart",
                ),
                cwd=tmp_path,
                timeout_seconds=30,
            )
            if result.succeeded:
                break
            await anyio.sleep(2)
        assert result.succeeded, result.stderr
    finally:
        await runner.run(
            (*compose, "down", "--volumes", "--remove-orphans"),
            cwd=tmp_path,
            timeout_seconds=60,
        )


def test_render_creates_opt_in_rabbitmq_cluster_with_stable_endpoint() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            rabbitmq_mode="cluster",
            rabbitmq_queue_type="quorum",
        )
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    environment = files[PurePosixPath("environment", ".env.example")]
    services = compose["services"]

    assert {"rabbitmq", "rabbitmq-0", "rabbitmq-1", "rabbitmq-2"} <= set(
        services
    )
    assert services["rabbitmq"]["image"] == "haproxy:3.0-alpine"
    assert services["rabbitmq"]["ports"] == [
        "${LOCAL_BIND_ADDRESS:-127.0.0.1}:${RABBITMQ_AMQP_PORT:-25672}:5672",
        "${LOCAL_BIND_ADDRESS:-127.0.0.1}:${RABBITMQ_MANAGEMENT_PORT:-25673}:15672",
    ]
    assert services["rabbitmq"]["healthcheck"]["test"] == [
        "CMD-SHELL",
        "nc -z 127.0.0.1 5672",
    ]
    for index in range(3):
        node = services[f"rabbitmq-{index}"]
        assert node["environment"]["RABBITMQ_NODENAME"] == f"rabbit@rabbitmq-{index}"
        assert node["environment"]["RABBITMQ_ERLANG_COOKIE"] == (
            "${RABBITMQ_ERLANG_COOKIE:?set RABBITMQ_ERLANG_COOKIE}"
        )
        assert "depends_on" not in node
        assert f"rabbitmq-{index}-data" in compose["volumes"]
        assert files[
            PurePosixPath("environment", "rabbitmq", f"rabbitmq-{index}.conf")
        ] == files[PurePosixPath("environment", "rabbitmq", "rabbitmq-0.conf")]
    assert "RABBITMQ_ERLANG_COOKIE=replace-with-a-long-random-secret" in environment
    assert "rabbitmq:5672" in environment
    assert "cluster_formation.peer_discovery_backend = classic_config" in files[
        PurePosixPath("environment", "rabbitmq", "rabbitmq-0.conf")
    ]
    assert "cluster_partition_handling = pause_minority" in files[
        PurePosixPath("environment", "rabbitmq", "rabbitmq-0.conf")
    ]
    assert "server rabbitmq-2 rabbitmq-2:5672 check" in files[
        PurePosixPath("environment", "rabbitmq", "haproxy.cfg")
    ]


def test_render_connects_rag_consumers_to_the_shared_network() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(enabled=True, durable_jobs=True, application=True, rag=True)
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    environment = files[PurePosixPath("environment", ".env.example")]
    readme = files[PurePosixPath("environment", "README.md")]

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
    durable_worker_probe = compose["services"]["durable-job-worker"]["healthcheck"][
        "test"
    ][3]
    assert "urlopen(os.environ['RAG_SEARCH_URL'] + '/_cluster/health', timeout=2)" in durable_worker_probe
    assert "urlopen(os.environ['RAG_OLLAMA_URL'] + '/api/tags', timeout=2)" in durable_worker_probe
    assert "RAG_NETWORK_NAME=kis_auto_trading-rag" in environment
    assert "RAG_SEARCH_BACKEND=elasticsearch" in environment
    assert "RAG_SEARCH_URL=http://elasticsearch:9200" in environment
    assert "RAG_OLLAMA_URL=http://ollama:11434" in environment
    assert "RAG_EMBEDDING_MODEL=embeddinggemma" in environment
    assert "start the RAG and inference profiles before this profile" in readme
    assert "../deploy/rag/README.md" in readme


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


def test_render_routes_clustered_rag_search_through_stable_proxy() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            durable_jobs=True,
            application=True,
            rag=True,
            rag_search_mode="cluster",
        )
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    environment = files[PurePosixPath("environment", ".env.example")]

    assert (
        compose["services"]["application"]["environment"]["RAG_SEARCH_URL"]
        == "${RAG_SEARCH_URL:-http://search:9200}"
    )
    assert "RAG_SEARCH_URL=http://search:9200" in environment


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
    assert {
        "airflow-db-bootstrap",
        "airflow-init",
        "airflow-webserver",
        "airflow-scheduler",
    } <= set(airflow)
    assert airflow["airflow-db-bootstrap"]["depends_on"] == {
        "postgres": {"condition": "service_healthy"}
    }
    assert "CREATE DATABASE airflow" in airflow["airflow-db-bootstrap"]["command"][2]
    assert airflow["airflow-init"]["depends_on"] == {
        "airflow-db-bootstrap": {"condition": "service_completed_successfully"}
    }
    assert airflow["airflow-init"]["command"] == ["airflow", "db", "migrate"]
    assert airflow["airflow-webserver"]["command"] == (
        "webserver --pid /tmp/airflow-webserver.pid"
    )
    assert airflow["airflow-scheduler"]["command"] == "scheduler"
    assert airflow["airflow-webserver"]["environment"]["DURABLE_JOB_API_TOKEN"] == "${DURABLE_JOB_API_TOKEN:?set DURABLE_JOB_API_TOKEN}"
    assert "../airflow/dags:/opt/airflow/dags:ro" in airflow["airflow-scheduler"]["volumes"]
    assert "airflow-home:/opt/airflow" in airflow["airflow-init"]["volumes"]
    assert "DURABLE_JOB_API_TOKEN=change-me" in environment
    assert "('airflow')" in databases
    assert "Airflow" in readme


def test_render_creates_opt_in_airflow_scheduler_ha() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            durable_jobs=True,
            postgres_mode="ha",
            airflow_scheduler_replicas=2,
        )
    )

    compose = yaml.safe_load(
        files[PurePosixPath("environment", "compose.integration.yml")]
    )
    environment = files[PurePosixPath("environment", ".env.example")]
    readme = files[PurePosixPath("environment", "README.md")]
    services = compose["services"]

    assert "airflow-scheduler" not in services
    assert {"airflow-scheduler-0", "airflow-scheduler-1"} <= set(services)
    assert services["airflow-init"]["command"] == ["airflow", "db", "migrate"]
    assert services["airflow-webserver"]["command"] == (
        "webserver --pid /tmp/airflow-webserver.pid"
    )
    for index in range(2):
        scheduler = services[f"airflow-scheduler-{index}"]
        assert scheduler["command"] == "scheduler"
        assert scheduler["environment"]["AIRFLOW__CORE__EXECUTOR"] == "LocalExecutor"
        assert scheduler["environment"]["AIRFLOW__CORE__FERNET_KEY"] == (
            "${AIRFLOW_FERNET_KEY:?set AIRFLOW_FERNET_KEY}"
        )
        assert scheduler["environment"]["AIRFLOW__SCHEDULER__ENABLE_HEALTH_CHECK"] == "true"
        assert scheduler["environment"]["AIRFLOW__SCHEDULER__USE_ROW_LEVEL_LOCKING"] == "true"
        assert scheduler["healthcheck"]["test"] == [
            "CMD-SHELL",
            "curl --fail http://127.0.0.1:8974/health || exit 1",
        ]
        assert "ports" not in scheduler
    assert "AIRFLOW_FERNET_KEY=replace-with-a-valid-fernet-key" in environment
    assert "scheduler-process recovery only" in readme


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


def test_render_starts_domain_event_workers_without_durable_jobs() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(enabled=True, application=True)
    )

    compose = files[PurePosixPath("environment", "compose.integration.yml")]
    environment = files[PurePosixPath("environment", ".env.example")]
    readme = files[PurePosixPath("environment", "README.md")]

    assert "  migrate:" in compose
    assert "  application:" in compose
    assert "  airflow:" not in compose
    assert "  outbox-relay:" in compose
    assert "  message-worker:" in compose
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
    assert "  message-worker:" in compose
    assert "command: [\"python\", \"scripts/run_message_worker.py\"]" in compose
    assert "  durable-job-worker:" in compose
    assert "command: [\"python\", \"scripts/run_durable_job_worker.py\"]" in compose
    assert "condition: service_completed_successfully" in compose
    assert "DURABLE_JOB_API_URL: ${DURABLE_JOB_API_URL:-http://application:8000}" in compose
    assert "DURABLE_JOB_API_TOKEN: ${DURABLE_JOB_API_TOKEN:?set DURABLE_JOB_API_TOKEN}" in compose
    assert "APPLICATION_PORT=28000" in environment
    assert "DURABLE_JOB_API_URL=http://application:8000" in environment
    assert "migrations run before the generated application starts" in readme


def test_durable_job_worker_receives_the_declared_redis_cluster_environment() -> None:
    compose = yaml.safe_load(
        LocalEnvironmentGenerator().render(
            integration_specification(enabled=True, durable_jobs=True, application=True)
        )[PurePosixPath("environment", "compose.integration.yml")]
    )

    worker = compose["services"]["durable-job-worker"]

    assert worker["environment"]["REDIS_CLUSTER_URL"] == (
        "${REDIS_CLUSTER_URL:-redis://redis-7000:7000}"
    )
    assert "REDIS_CLUSTER_STARTUP_NODES" in worker["environment"]
    assert worker["depends_on"]["redis-cluster-init"] == {
        "condition": "service_completed_successfully"
    }


def test_message_worker_receives_realtime_redis_runtime() -> None:
    compose = yaml.safe_load(
        LocalEnvironmentGenerator().render(
            integration_specification(
                enabled=True,
                application=True,
                realtime_backplane="redis_pubsub",
            )
        )[PurePosixPath("environment", "compose.integration.yml")]
    )

    worker = compose["services"]["message-worker"]

    assert worker["environment"]["REDIS_CLUSTER_URL"] == (
        "${REDIS_CLUSTER_URL:-redis://redis-7000:7000}"
    )
    assert "REDIS_CLUSTER_STARTUP_NODES" in worker["environment"]
    assert worker["depends_on"]["redis-cluster-init"] == {
        "condition": "service_completed_successfully"
    }


def test_application_receives_all_service_tokens_but_airflow_receives_only_its_scope() -> None:
    specification = integration_specification(
        enabled=True,
        durable_jobs=True,
        application=True,
    )
    application = specification.application.model_copy(
        update={
            "service_tokens": [
                ServiceTokenSpec(
                    name="operator", token_env="OPERATOR_API_TOKEN"
                )
            ]
        }
    )

    compose = yaml.safe_load(
        LocalEnvironmentGenerator().render(
            specification.model_copy(update={"application": application})
        )[PurePosixPath("environment", "compose.integration.yml")]
    )

    assert compose["services"]["application"]["environment"][
        "OPERATOR_API_TOKEN"
    ] == "${OPERATOR_API_TOKEN:?set OPERATOR_API_TOKEN}"
    assert "OPERATOR_API_TOKEN" not in compose["services"]["airflow-webserver"][
        "environment"
    ]


def test_durable_job_worker_receives_control_plane_heartbeat_environment() -> None:
    files = LocalEnvironmentGenerator().render(
        integration_specification(
            enabled=True,
            durable_jobs=True,
            application=True,
            heartbeat_reporter=True,
        )
    )
    compose = files[PurePosixPath("environment", "compose.integration.yml")]

    durable_worker = compose.split("  durable-job-worker:\n", maxsplit=1)[1]
    assert "CONTROL_PLANE_HEARTBEAT_URL: ${CONTROL_PLANE_HEARTBEAT_URL:-}" in durable_worker
    assert "CONTROL_PLANE_API_TOKEN: ${CONTROL_PLANE_API_TOKEN:-}" in durable_worker


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
        "message-worker",
        "durable-job-worker",
        "airflow-webserver",
        "airflow-scheduler",
    ):
        assert services[service_name]["restart"] == "unless-stopped"

    assert services["migrate"]["restart"] == "no"
    assert services["redis-cluster-init"]["restart"] == "no"
    assert services["airflow-init"].get("restart") is None
    assert services["rabbitmq"]["healthcheck"]["test"] == [
        "CMD-SHELL",
        "rabbitmq-diagnostics -q check_port_connectivity",
    ]
    assert services["durable-job-worker"]["healthcheck"]["test"] == [
        "CMD",
        "python",
        "-c",
        "import asyncio, os, aio_pika; connection = asyncio.run(aio_pika.connect(os.environ['RABBITMQ_URL'], timeout=2)); asyncio.run(connection.close())",
    ]
    assert services["outbox-relay"]["healthcheck"]["test"] == services[
        "durable-job-worker"
    ]["healthcheck"]["test"]
    assert services["message-worker"]["healthcheck"]["test"] == services[
        "durable-job-worker"
    ]["healthcheck"]["test"]
    assert services["application"]["healthcheck"]["test"] == [
        "CMD",
        "python",
        "-c",
        "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/readiness').read()",
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


def test_sentinel_renders_primary_replicas_and_quorum() -> None:
    specification = integration_specification(
        enabled=True,
        application=True,
        key_value_store_backend="redis",
        key_value_store_mode="sentinel",
    )
    sentinel = specification.application.services[0].model_copy(
        update={"mode": "sentinel"}
    )
    application = specification.application.model_copy(
        update={"services": [sentinel, specification.application.services[1]]}
    )

    files = LocalEnvironmentGenerator().render(
        specification.model_copy(update={"application": application})
    )
    compose = yaml.safe_load(files[PurePosixPath("environment/compose.integration.yml")])
    environment = files[PurePosixPath("environment/.env.example")]
    sentinel_config = files[PurePosixPath("environment/redis-sentinel/sentinel.conf")]

    for index in range(1, 3):
        assert f"redis-sentinel-primary-{index}" in compose["services"]
        for replica in range(1, 3):
            assert f"redis-sentinel-replica-{index}-{replica}" in compose["services"]
    for index in range(1, 4):
        sentinel_service = compose["services"][f"redis-sentinel-{index}"]
        assert sentinel_service["depends_on"]["redis-sentinel-primary-1"] == {
            "condition": "service_healthy"
        }
        assert sentinel_service["depends_on"]["redis-sentinel-primary-2"] == {
            "condition": "service_healthy"
        }
        assert sentinel_service["depends_on"]["redis-sentinel-replica-1-1"] == {
            "condition": "service_healthy"
        }
        assert sentinel_service["volumes"][0] == (
            "./redis-sentinel/sentinel.conf:/bootstrap/sentinel.conf:ro"
        )
    assert "sentinel monitor session-primary redis-sentinel-primary-1 6379 2" in sentinel_config
    assert "sentinel monitor cache-primary redis-sentinel-primary-2 6379 2" in sentinel_config
    assert "sentinel resolve-hostnames yes" in sentinel_config
    assert "sentinel announce-hostnames yes" not in sentinel_config
    assert "REDIS_SENTINEL_URLS=redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379" in environment
    application_service = compose["services"]["application"]
    assert application_service["depends_on"]["redis-sentinel-1"] == {
        "condition": "service_healthy"
    }
    assert "REDIS_SENTINEL_URLS" in application_service["environment"]
