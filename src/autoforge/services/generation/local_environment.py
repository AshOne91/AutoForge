from pathlib import PurePosixPath

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
    specification_hash,
)
from autoforge.core.specification import DatabaseStoreSpec, ProjectSpec, ServiceSpec

LOCAL_ENVIRONMENT_GENERATOR_ID = "autoforge.generator.local-environment"
LOCAL_ENVIRONMENT_GENERATOR_VERSION = "0.1.0"


class LocalEnvironmentGenerator:
    """Generate disposable Docker services for local integration validation."""

    @property
    def generator_id(self) -> str:
        return LOCAL_ENVIRONMENT_GENERATOR_ID

    @property
    def generator_version(self) -> str:
        return LOCAL_ENVIRONMENT_GENERATOR_VERSION

    def render(self, specification: ProjectSpec) -> dict[PurePosixPath, str]:
        if not specification.tooling.local_environment.enabled:
            return {}
        redis_mode = self._redis_mode(specification.application.services)
        postgres_mode = specification.tooling.local_environment.postgres_mode
        redis_service = next(
            (
                service
                for service in specification.application.services
                if service.kind == "redis_session"
            ),
            None,
        )
        rabbitmq_services = [
            service
            for service in specification.application.services
            if service.kind == "rabbitmq"
        ]
        if len(rabbitmq_services) > 1:
            raise ValueError("local environment supports one RabbitMQ service")
        if not specification.application.databases and redis_mode is None and not rabbitmq_services:
            raise ValueError("local environment requires a declared database or service")
        has_durable_jobs = bool(specification.application.durable_jobs)
        has_application = specification.tooling.local_environment.application_enabled
        has_migration = has_application and bool(specification.application.databases)
        has_rag = specification.tooling.rag.enabled
        host_port_base = specification.tooling.local_environment.host_port_base
        database_names = self._database_names(specification.application.databases)
        if has_durable_jobs and "airflow" not in database_names:
            database_names.append("airflow")

        files = {
            PurePosixPath("environment", "compose.integration.yml"): self._render_compose(
                specification,
                database_names=database_names,
                postgres_mode=postgres_mode,
                redis_mode=redis_mode,
                redis_service=redis_service,
                has_rabbitmq=bool(rabbitmq_services),
                has_durable_jobs=has_durable_jobs,
                has_application=has_application,
                has_migration=has_migration,
                has_rag=has_rag,
                host_port_base=host_port_base,
            ),
            PurePosixPath("environment", ".env.example"): self._render_env(
                specification,
                postgres_mode=postgres_mode,
                redis_mode=redis_mode,
                redis_service=redis_service,
                has_rabbitmq=bool(rabbitmq_services),
                has_durable_jobs=has_durable_jobs,
                has_application=has_application,
                has_rag=has_rag,
                host_port_base=host_port_base,
            ),
            PurePosixPath("environment", "README.md"): self._render_readme(
                redis_mode=redis_mode,
                postgres_mode=postgres_mode,
                has_rabbitmq=bool(rabbitmq_services),
                has_durable_jobs=has_durable_jobs,
                has_application=has_application,
                has_migration=has_migration,
            ),
        }
        if database_names:
            files[
                PurePosixPath("environment", "postgres-init", "00-databases.sql")
            ] = self._render_database_initialization(database_names)
        if postgres_mode == "ha" and database_names:
            files[PurePosixPath("environment", "postgres-ha", "haproxy.cfg")] = (
                self._render_postgres_ha_haproxy_config()
            )
        return files

    def plan(self, specification: ProjectSpec) -> GenerationPlan:
        rendered = self.render(specification)
        spec_hash = specification_hash(specification)
        return GenerationPlan(
            specification_version=specification.spec_version,
            specification_hash=spec_hash,
            files=[
                PlannedFile(
                    relative_path=path,
                    generator_id=self.generator_id,
                    generator_version=self.generator_version,
                    ownership=FileOwnership.GENERATED,
                    action=PlannedAction.CREATE,
                    specification_hash=spec_hash,
                    expected_content_hash=content_hash(content),
                    source="project:local-environment",
                )
                for path, content in sorted(rendered.items(), key=lambda item: item[0].as_posix())
            ],
        )

    @staticmethod
    def _database_names(databases: list[DatabaseStoreSpec]) -> list[str]:
        return [
            database.name
            if database.global_url_env is not None
            else f"{database.name}_shard_{shard.shard_id}"
            for database in databases
            for shard in (database.shards or [None])
        ]

    @staticmethod
    def _redis_mode(services: list[ServiceSpec]) -> str | None:
        modes = {
            service.mode
            for service in services
            if service.kind == "redis_session"
        }
        if len(modes) > 1:
            raise ValueError("local environment requires one Redis mode")
        if modes == {"sentinel"}:
            raise ValueError("local environment does not yet support Redis Sentinel")
        return next(iter(modes), None)

    def _render_compose(
        self,
        specification: ProjectSpec,
        *,
        database_names: list[str],
        postgres_mode: str,
        redis_mode: str | None,
        redis_service: ServiceSpec | None,
        has_rabbitmq: bool,
        has_durable_jobs: bool,
        has_application: bool,
        has_migration: bool,
        has_rag: bool,
        host_port_base: int | None,
    ) -> str:
        services: list[str] = []
        if specification.application.databases:
            if postgres_mode == "ha":
                services.extend(self._render_postgres_ha(database_names, host_port_base))
            else:
                services.append(self._render_postgres(host_port_base))
        if redis_mode == "standalone":
            services.append(self._render_redis_standalone())
        elif redis_mode == "cluster":
            services.extend(self._render_redis_cluster())
        if has_rabbitmq:
            services.append(self._render_rabbitmq(host_port_base))
        if has_application:
            if has_migration:
                services.append(self._render_migrate(specification, postgres_mode))
            services.append(
                self._render_application(
                    specification,
                    redis_mode=redis_mode,
                    redis_service=redis_service,
                    has_durable_jobs=has_durable_jobs,
                    has_migration=has_migration,
                    has_rag=has_rag,
                    host_port_base=host_port_base,
                )
            )
            if has_durable_jobs:
                services.append(self._render_outbox_relay(specification))
                services.append(
                    self._render_durable_job_worker(
                        specification, has_rag=has_rag
                    )
                )
        if has_durable_jobs:
            services.append(
                self._render_airflow(
                    has_application=has_application,
                    postgres_mode=postgres_mode,
                    host_port_base=host_port_base,
                )
            )
        return (
            f"name: {specification.project.package_name}-integration\n"
            "\n"
            "services:\n"
            + "\n".join(services)
            + (
                "\nnetworks:\n"
                "  rag:\n"
                f"    name: ${{RAG_NETWORK_NAME:-{specification.project.package_name}-rag}}\n"
                "    external: true\n"
                if has_rag
                else ""
            )
            + self._render_volumes(
                postgres_mode=postgres_mode,
                redis_mode=redis_mode,
                has_durable_jobs=has_durable_jobs,
            )
        )

    @staticmethod
    def _render_volumes(
        *, postgres_mode: str, redis_mode: str | None, has_durable_jobs: bool
    ) -> str:
        names = (
            [f"postgres-ha-{index}-data" for index in range(3)]
            + [f"etcd-{index}-data" for index in range(3)]
            if postgres_mode == "ha"
            else []
        ) + (
            [f"redis-{port}-data" for port in range(7000, 7006)]
            if redis_mode == "cluster"
            else []
        )
        if has_durable_jobs:
            names.append("airflow-home")
        return "\nvolumes:\n" + "".join(f"  {name}:\n" for name in names) if names else ""

    @staticmethod
    def _host_port(host_port_base: int | None, *, default: int, offset: int) -> int:
        return default if host_port_base is None else host_port_base + offset

    @classmethod
    def _render_postgres(cls, host_port_base: int | None) -> str:
        postgres_port = cls._host_port(host_port_base, default=25432, offset=10)
        return (
            "  postgres:\n"
            "    image: postgres:16-alpine\n"
            "    restart: unless-stopped\n"
            "    environment:\n"
            "      POSTGRES_USER: ${POSTGRES_USER:-autoforge}\n"
            "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change-me}\n"
            "      POSTGRES_DB: postgres\n"
            "    ports:\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{POSTGRES_PORT:-{postgres_port}}}:5432\"\n"
            "    volumes:\n"
            "      - ./postgres-init/00-databases.sql:/docker-entrypoint-initdb.d/00-databases.sql:ro\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"pg_isready -U $$POSTGRES_USER -d postgres\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )

    @classmethod
    def _render_postgres_ha(
        cls, database_names: list[str], host_port_base: int | None
    ) -> list[str]:
        postgres_port = cls._host_port(host_port_base, default=25432, offset=10)
        services = [cls._render_etcd(index) for index in range(3)]
        services.extend(cls._render_postgres_ha_node(index) for index in range(3))
        services.extend(
            [
                (
                    "  postgres:\n"
                    "    image: haproxy:3.0-alpine\n"
                    "    restart: unless-stopped\n"
                    "    ports:\n"
                    f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{POSTGRES_PORT:-{postgres_port}}}:5432\"\n"
                    "    volumes:\n"
                    "      - ./postgres-ha/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro\n"
                    "    depends_on:\n"
                    "      postgres-ha-0:\n"
                    "        condition: service_started\n"
                    "      postgres-ha-1:\n"
                    "        condition: service_started\n"
                    "      postgres-ha-2:\n"
                    "        condition: service_started\n"
                    "    healthcheck:\n"
                    "      test: [\"CMD-SHELL\", \"haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg\"]\n"
                    "      interval: 3s\n"
                    "      timeout: 3s\n"
                    "      retries: 20\n"
                ),
                cls._render_postgres_ha_init(database_names),
            ]
        )
        return services

    @staticmethod
    def _render_etcd(index: int) -> str:
        cluster = ",".join(
            f"etcd-{member}=http://etcd-{member}:2380" for member in range(3)
        )
        return (
            f"  etcd-{index}:\n"
            "    image: quay.io/coreos/etcd:v3.5.18\n"
            "    restart: unless-stopped\n"
            "    command:\n"
            "      - /usr/local/bin/etcd\n"
            f"      - --name=etcd-{index}\n"
            "      - --data-dir=/etcd-data\n"
            f"      - --initial-advertise-peer-urls=http://etcd-{index}:2380\n"
            "      - --listen-peer-urls=http://0.0.0.0:2380\n"
            f"      - --advertise-client-urls=http://etcd-{index}:2379\n"
            "      - --listen-client-urls=http://0.0.0.0:2379\n"
            f"      - --initial-cluster={cluster}\n"
            "      - --initial-cluster-state=new\n"
            "      - --initial-cluster-token=autoforge-postgres-ha\n"
            "    volumes:\n"
            f"      - etcd-{index}-data:/etcd-data\n"
            "    healthcheck:\n"
            "      test: [\"CMD\", \"/usr/local/bin/etcdctl\", \"endpoint\", \"health\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )

    @staticmethod
    def _render_postgres_ha_node(index: int) -> str:
        return (
            f"  postgres-ha-{index}:\n"
            "    image: ghcr.io/zalando/spilo-16:3.3-p3\n"
            "    restart: unless-stopped\n"
            "    environment:\n"
            "      SPILO_PROVIDER: local\n"
            "      SCOPE: ${POSTGRES_HA_SCOPE:-autoforge-postgres}\n"
            "      ETCD3_HOSTS: etcd-0:2379,etcd-1:2379,etcd-2:2379\n"
            f"      RESTAPI_CONNECT_ADDRESS: postgres-ha-{index}\n"
            "      PGPASSWORD_SUPERUSER: ${POSTGRES_PASSWORD:-change-me}\n"
            "      PGUSER_STANDBY: replication\n"
            "      PGPASSWORD_STANDBY: ${POSTGRES_REPLICATION_PASSWORD:-change-me-replication}\n"
            "      ALLOW_NOSSL: \"true\"\n"
            "      SPILO_CONFIGURATION: |-\n"
            "        postgresql:\n"
            f"          connect_address: postgres-ha-{index}:5432\n"
            "        bootstrap:\n"
            "          dcs:\n"
            "            ttl: 10\n"
            "            loop_wait: 3\n"
            "            retry_timeout: 10\n"
            "            maximum_lag_on_failover: 1048576\n"
            "            synchronous_mode: true\n"
            "            synchronous_mode_strict: false\n"
            "            postgresql:\n"
            "              parameters:\n"
            "                wal_level: replica\n"
            "                max_wal_senders: 10\n"
            "                max_replication_slots: 10\n"
            "                hot_standby: \"on\"\n"
            "                synchronous_commit: \"on\"\n"
            "    volumes:\n"
            f"      - postgres-ha-{index}-data:/home/postgres/pgdata\n"
            "    depends_on:\n"
            "      etcd-0:\n"
            "        condition: service_healthy\n"
            "      etcd-1:\n"
            "        condition: service_healthy\n"
            "      etcd-2:\n"
            "        condition: service_healthy\n"
            + (
                f"      postgres-ha-{index - 1}:\n"
                "        condition: service_healthy\n"
                if index > 0
                else ""
            )
            + "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"curl -fsS http://localhost:8008/health || exit 1\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 30\n"
        )

    @staticmethod
    def _render_postgres_ha_init(database_names: list[str]) -> str:
        requested_databases = ", ".join(f"('{name}')" for name in database_names)
        return (
            "  postgres-ha-init:\n"
            "    image: postgres:16-alpine\n"
            "    environment:\n"
            "      POSTGRES_SUPERUSER: postgres\n"
            "      POSTGRES_USER: ${POSTGRES_USER:-autoforge}\n"
            "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change-me}\n"
            "      PGPASSWORD: ${POSTGRES_PASSWORD:-change-me}\n"
            "    volumes:\n"
            "      - ./postgres-init/00-databases.sql:/postgres-init/00-databases.sql:ro\n"
            "    depends_on:\n"
            "      postgres:\n"
            "        condition: service_healthy\n"
            "    command:\n"
            "      - /bin/sh\n"
            "      - -ec\n"
            "      - |-\n"
            "        until psql -h postgres -U $$POSTGRES_SUPERUSER -d postgres -c 'SELECT 1' >/dev/null 2>&1; do sleep 1; done\n"
            "        psql -h postgres -U $$POSTGRES_SUPERUSER -d postgres -v ON_ERROR_STOP=1 -v application_user=\"$$POSTGRES_USER\" -v application_password=\"$$POSTGRES_PASSWORD\" <<'SQL'\n"
            "        SELECT format('CREATE ROLE %I LOGIN', :'application_user')\n"
            "        WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'application_user')\n"
            "        \\gexec\n"
            "        SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'application_user', :'application_password')\n"
            "        \\gexec\n"
            "        SQL\n"
            "        psql -h postgres -U $$POSTGRES_SUPERUSER -d postgres -v ON_ERROR_STOP=1 -f /postgres-init/00-databases.sql\n"
            "        psql -h postgres -U $$POSTGRES_SUPERUSER -d postgres -v ON_ERROR_STOP=1 -v application_user=\"$$POSTGRES_USER\" <<'SQL'\n"
            "        SELECT format('ALTER DATABASE %I OWNER TO %I', database_name, :'application_user')\n"
            f"        FROM (VALUES {requested_databases}) AS requested(database_name)\n"
            "        \\gexec\n"
            "        SQL\n"
            "    restart: \"no\"\n"
        )

    @staticmethod
    def _render_database_initialization(database_names: list[str]) -> str:
        requested_databases = ", ".join(f"('{name}')" for name in database_names)
        return (
            "SELECT format('CREATE DATABASE %I', database_name)\n"
            f"FROM (VALUES {requested_databases}) AS requested(database_name)\n"
            "WHERE NOT EXISTS (\n"
            "  SELECT 1 FROM pg_database WHERE datname = requested.database_name\n"
            ")\n"
            "\\gexec\n"
        )

    @staticmethod
    def _render_postgres_ha_haproxy_config() -> str:
        return (
            "global\n"
            "  log stdout format raw local0\n"
            "\n"
            "defaults\n"
            "  mode tcp\n"
            "  timeout connect 5s\n"
            "  timeout client 60s\n"
            "  timeout server 60s\n"
            "\n"
            "frontend postgres-write\n"
            "  bind *:5432\n"
            "  default_backend postgres-primary\n"
            "\n"
            "backend postgres-primary\n"
            "  option httpchk GET /primary\n"
            "  http-check expect status 200\n"
            "  server postgres-ha-0 postgres-ha-0:5432 check port 8008\n"
            "  server postgres-ha-1 postgres-ha-1:5432 check port 8008\n"
            "  server postgres-ha-2 postgres-ha-2:5432 check port 8008\n"
        )

    @staticmethod
    def _render_redis_standalone() -> str:
        return (
            "  redis:\n"
            "    image: redis:7-alpine\n"
            "    restart: unless-stopped\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"redis-cli ping | grep -q PONG\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )

    @staticmethod
    def _render_redis_cluster() -> list[str]:
        nodes = [
            (
                f"  redis-{port}:\n"
                "    image: redis:7-alpine\n"
                "    restart: unless-stopped\n"
                "    command:\n"
                "      - redis-server\n"
                f"      - --port\n      - \"{port}\"\n"
                "      - --cluster-enabled\n      - yes\n"
                "      - --cluster-config-file\n      - nodes.conf\n"
                "      - --cluster-node-timeout\n      - \"5000\"\n"
                f"      - --cluster-announce-hostname\n      - redis-{port}\n"
                "      - --cluster-preferred-endpoint-type\n      - hostname\n"
                "      - --appendonly\n      - yes\n"
                "    volumes:\n"
                f"      - redis-{port}-data:/data\n"
                "    healthcheck:\n"
                f"      test: [\"CMD-SHELL\", \"redis-cli -p {port} ping | grep -q PONG\"]\n"
                "      interval: 3s\n"
                "      timeout: 3s\n"
                "      retries: 20\n"
            )
            for port in range(7000, 7006)
        ]
        cluster_nodes = " ".join(
            f"redis-{port}:{port}" for port in range(7000, 7006)
        )
        dependencies = "".join(
            f"      redis-{port}:\n        condition: service_healthy\n"
            for port in range(7000, 7006)
        )
        nodes.append(
            "  redis-cluster-init:\n"
            "    image: redis:7-alpine\n"
            "    depends_on:\n"
            + dependencies
            + "    command:\n"
            "      - /bin/sh\n"
            "      - -c\n"
            "      - |-\n"
            "        if redis-cli -h redis-7000 -p 7000 cluster nodes | grep -q '[0-9]-[0-9]'; then\n"
            "          for port in 7001 7002 7003 7004 7005; do\n"
            "            set -- $$(getent hosts redis-$$port)\n"
            "            redis-cli -h redis-7000 -p 7000 cluster meet \"$$1\" \"$$port\"\n"
            "          done\n"
            "          for _ in $(seq 1 20); do\n"
            "            topology=$(redis-cli -h redis-7000 -p 7000 cluster nodes)\n"
            "            masters=$(printf '%s\\n' \"$$topology\" | awk '$3 ~ /master/ && $8 == \"connected\" { count++ } END { print count + 0 }')\n"
            "            replicas=$(printf '%s\\n' \"$$topology\" | awk '$3 ~ /slave/ && $8 == \"connected\" { count++ } END { print count + 0 }')\n"
            "            redis-cli -h redis-7000 -p 7000 cluster info | grep -q 'cluster_state:ok' && [ \"$$masters\" -eq 3 ] && [ \"$$replicas\" -eq 3 ] && exit 0\n"
            "            sleep 1\n"
            "          done\n"
            "          echo 'existing Redis cluster did not meet the 3-primary/3-replica topology' >&2\n"
            "          exit 1\n"
            "        fi\n"
            f"        exec redis-cli --cluster create {cluster_nodes} --cluster-replicas 1 --cluster-yes\n"
            "    restart: \"no\"\n"
        )
        return nodes

    @classmethod
    def _render_rabbitmq(cls, host_port_base: int | None) -> str:
        amqp_port = cls._host_port(host_port_base, default=25672, offset=30)
        management_port = cls._host_port(host_port_base, default=25673, offset=31)
        return (
            "  rabbitmq:\n"
            "    image: rabbitmq:4.1-management-alpine\n"
            "    restart: unless-stopped\n"
            "    environment:\n"
            "      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-autoforge}\n"
            "      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-change-me}\n"
            "    ports:\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{RABBITMQ_AMQP_PORT:-{amqp_port}}}:5672\"\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{RABBITMQ_MANAGEMENT_PORT:-{management_port}}}:15672\"\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"rabbitmq-diagnostics -q ping\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )

    @staticmethod
    def _render_database_environment(specification: ProjectSpec) -> str:
        lines: list[str] = []
        for database in specification.application.databases:
            targets = [(database.name, database.global_url_env)]
            targets.extend(
                (f"{database.name}_shard_{shard.shard_id}", shard.url_env)
                for shard in database.shards
            )
            for database_name, environment_name in targets:
                if environment_name is not None:
                    lines.append(
                        "      "
                        f"{environment_name}: postgresql+asyncpg://${{POSTGRES_USER:-autoforge}}:${{POSTGRES_PASSWORD:-change-me}}@postgres:5432/{database_name}\n"
                    )
        return "".join(lines)

    @staticmethod
    def _application_image(specification: ProjectSpec) -> str:
        return specification.project.package_name.replace("_", "-") + ":local"

    @staticmethod
    def _render_rag_environment(specification: ProjectSpec) -> str:
        search_backend = specification.tooling.rag.search_backend
        return (
            f"      RAG_SEARCH_BACKEND: ${{RAG_SEARCH_BACKEND:-{search_backend}}}\n"
            f"      RAG_SEARCH_URL: ${{RAG_SEARCH_URL:-http://{search_backend}:9200}}\n"
            "      RAG_OLLAMA_URL: ${RAG_OLLAMA_URL:-http://ollama:11434}\n"
            "      RAG_EMBEDDING_MODEL: ${RAG_EMBEDDING_MODEL:-embeddinggemma}\n"
        )

    def _render_migrate(self, specification: ProjectSpec, postgres_mode: str) -> str:
        image = self._application_image(specification)
        return (
            "  migrate:\n"
            "    build:\n"
            "      context: ..\n"
            "      dockerfile: Dockerfile\n"
            f"    image: ${{APPLICATION_IMAGE:-{image}}}\n"
            "    pull_policy: never\n"
            "    command: [\"python\", \"scripts/migrate.py\"]\n"
            "    environment:\n"
            + self._render_database_environment(specification)
            + "    depends_on:\n"
            + (
                "      postgres-ha-init:\n"
                "        condition: service_completed_successfully\n"
                if postgres_mode == "ha"
                else "      postgres:\n        condition: service_healthy\n"
            )
            + "    restart: \"no\"\n"
        )

    def _render_application(
        self,
        specification: ProjectSpec,
        *,
        redis_mode: str | None,
        redis_service: ServiceSpec | None,
        has_durable_jobs: bool,
        has_migration: bool,
        has_rag: bool,
        host_port_base: int | None,
    ) -> str:
        image = self._application_image(specification)
        application_port = self._host_port(host_port_base, default=28000, offset=0)
        redis_environment = ""
        dependencies: list[str] = []
        if has_migration:
            dependencies.append(
                "      migrate:\n"
                "        condition: service_completed_successfully\n"
            )
        if redis_mode == "standalone":
            redis_environment = "      REDIS_URL: ${REDIS_URL:-redis://redis:6379}\n"
            dependencies.append("      redis:\n        condition: service_healthy\n")
        elif redis_mode == "cluster":
            redis_environment = (
                f"      {redis_service.cluster_url_env}: "
                f"${{{redis_service.cluster_url_env}:-redis://redis-7000:7000}}\n"
                f"      {redis_service.cluster_startup_nodes_env}: "
                f"${{{redis_service.cluster_startup_nodes_env}:-redis://redis-7000:7000,redis://redis-7001:7001,redis://redis-7002:7002,redis://redis-7003:7003,redis://redis-7004:7004,redis://redis-7005:7005}}\n"
            )
            dependencies.append(
                "      redis-cluster-init:\n"
                "        condition: service_completed_successfully\n"
            )
        durable_job_environment = (
            "      DURABLE_JOB_API_TOKEN: ${DURABLE_JOB_API_TOKEN:?set DURABLE_JOB_API_TOKEN}\n"
            if has_durable_jobs
            else ""
        )
        rag_environment = self._render_rag_environment(specification) if has_rag else ""
        dependency_targets: list[tuple[str, int]] = []
        if specification.application.databases:
            dependency_targets.append(("postgres", 5432))
        if redis_mode == "standalone":
            dependency_targets.append(("redis", 6379))
        dependency_probe = (
            "[socket.create_connection(target, 2).close() for target in "
            f"{dependency_targets!r}]"
            if dependency_targets
            else "[]"
        )
        healthcheck_imports = "from urllib.request import urlopen; import socket"
        healthcheck_probe = f"urlopen('http://127.0.0.1:8000/health').read(); {dependency_probe}"
        if redis_mode == "cluster":
            healthcheck_imports += "; import asyncio, os; from urllib.parse import urlparse; from redis.cluster import ClusterNode; from redis.asyncio.cluster import RedisCluster"
            healthcheck_probe += (
                f"; startup_nodes=[ClusterNode(urlparse(value).hostname, urlparse(value).port or 6379) for value in os.environ['{redis_service.cluster_startup_nodes_env}'].split(',')]; "
                f"client=RedisCluster.from_url(os.environ['{redis_service.cluster_url_env}'], "
                "startup_nodes=startup_nodes, "
                "decode_responses=True, require_full_coverage=True); "
                "asyncio.run(client.ping())"
            )
        elif redis_mode == "standalone":
            healthcheck_imports += "; import asyncio, os; from redis.asyncio import Redis"
            healthcheck_probe += (
                "; client=Redis.from_url(os.environ['REDIS_URL']); "
                "asyncio.run(client.ping())"
            )
        depends_on = (
            "    depends_on:\n" + "".join(dependencies)
            if dependencies
            else ""
        )
        rag_network = "    networks:\n      - default\n      - rag\n" if has_rag else ""
        return (
            "  application:\n"
            f"    image: ${{APPLICATION_IMAGE:-{image}}}\n"
            "    pull_policy: never\n"
            "    restart: unless-stopped\n"
            "    environment:\n"
            + self._render_database_environment(specification)
            + redis_environment
            + durable_job_environment
            + rag_environment
            + "      LOG_DIRECTORY: /app/logs\n"
            "    ports:\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{APPLICATION_PORT:-{application_port}}}:8000\"\n"
            "    volumes:\n"
            "      - ../logs:/app/logs\n"
            + rag_network
            + depends_on
            + "    healthcheck:\n"
            '      test: ["CMD", "python", "-c", '
            f'"{healthcheck_imports}; {healthcheck_probe}"]\n'
            "      interval: 5s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )

    def _render_outbox_relay(self, specification: ProjectSpec) -> str:
        image = self._application_image(specification)
        return (
            "  outbox-relay:\n"
            f"    image: ${{APPLICATION_IMAGE:-{image}}}\n"
            "    pull_policy: never\n"
            "    restart: unless-stopped\n"
            "    command: [\"python\", \"scripts/run_outbox_relay.py\"]\n"
            "    healthcheck:\n"
            '      test: ["CMD", "python", "-c", "import asyncio, os, aio_pika; connection = asyncio.run(aio_pika.connect(os.environ[\'RABBITMQ_URL\'], timeout=2)); asyncio.run(connection.close())"]\n'
            "      interval: 10s\n"
            "      timeout: 3s\n"
            "      retries: 3\n"
            "    environment:\n"
            + self._render_database_environment(specification)
            + "      RABBITMQ_URL: ${RABBITMQ_URL:?set RABBITMQ_URL}\n"
            "    depends_on:\n"
            "      migrate:\n"
            "        condition: service_completed_successfully\n"
            "      rabbitmq:\n"
            "        condition: service_healthy\n"
        )

    def _render_durable_job_worker(
        self, specification: ProjectSpec, *, has_rag: bool
    ) -> str:
        image = self._application_image(specification)
        restart_policy = specification.application.durable_job_worker_restart_policy
        rag_network = "    networks:\n      - default\n      - rag\n" if has_rag else ""
        rag_environment = self._render_rag_environment(specification) if has_rag else ""
        return (
            "  durable-job-worker:\n"
            f"    image: ${{APPLICATION_IMAGE:-{image}}}\n"
            "    pull_policy: never\n"
            f'    restart: "{restart_policy}"\n'
            "    command: [\"python\", \"scripts/run_durable_job_worker.py\"]\n"
            "    healthcheck:\n"
            '      test: ["CMD", "python", "-c", "import asyncio, os, aio_pika; connection = asyncio.run(aio_pika.connect(os.environ[\'RABBITMQ_URL\'], timeout=2)); asyncio.run(connection.close())"]\n'
            "      interval: 10s\n"
            "      timeout: 3s\n"
            "      retries: 3\n"
            "    environment:\n"
            + self._render_database_environment(specification)
            + "      RABBITMQ_URL: ${RABBITMQ_URL:?set RABBITMQ_URL}\n"
            + rag_environment
            + rag_network
            + "    depends_on:\n"
            "      migrate:\n"
            "        condition: service_completed_successfully\n"
            "      rabbitmq:\n"
            "        condition: service_healthy\n"
        )

    @classmethod
    def _render_airflow(
        cls, *, has_application: bool, postgres_mode: str, host_port_base: int | None
    ) -> str:
        airflow_port = cls._host_port(host_port_base, default=28080, offset=40)
        api_url = (
            "http://application:8000"
            if has_application
            else "http://host.docker.internal:8000"
        )
        scheduler_dependencies = ""
        if has_application:
            scheduler_dependencies = (
                "      application:\n"
                "        condition: service_healthy\n"
                "      outbox-relay:\n"
                "        condition: service_started\n"
                "      durable-job-worker:\n"
                "        condition: service_started\n"
            )
        environment = (
            "      AIRFLOW__CORE__EXECUTOR: SequentialExecutor\n"
            "      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER:-autoforge}:${POSTGRES_PASSWORD:-change-me}@postgres:5432/airflow\n"
            "      AIRFLOW__CORE__LOAD_EXAMPLES: \"false\"\n"
            "      AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: \"true\"\n"
            f"      DURABLE_JOB_API_URL: ${{DURABLE_JOB_API_URL:-{api_url}}}\n"
            "      DURABLE_JOB_API_TOKEN: ${DURABLE_JOB_API_TOKEN:?set DURABLE_JOB_API_TOKEN}\n"
        )
        volumes = (
            "      - ../airflow/dags:/opt/airflow/dags:ro\n"
            "      - airflow-home:/opt/airflow\n"
        )
        return (
            "  airflow-init:\n"
            "    image: apache/airflow:2.10.5-python3.12\n"
            "    depends_on:\n"
            + (
                "      postgres-ha-init:\n"
                "        condition: service_completed_successfully\n"
                if postgres_mode == "ha"
                else "      postgres:\n        condition: service_healthy\n"
            )
            + "    environment:\n"
            + environment
            + "    volumes:\n"
            + volumes
            + "    command: [\"airflow\", \"db\", \"migrate\"]\n"
            "\n"
            "  airflow-webserver:\n"
            "    image: apache/airflow:2.10.5-python3.12\n"
            "    depends_on:\n"
            "      airflow-init:\n"
            "        condition: service_completed_successfully\n"
            "    environment:\n"
            + environment
            + "    volumes:\n"
            + volumes
            + "    ports:\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{AIRFLOW_PORT:-{airflow_port}}}:8080\"\n"
            "    command: webserver\n"
            "    restart: unless-stopped\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"curl --fail http://localhost:8080/health || exit 1\"]\n"
            "      interval: 10s\n"
            "      timeout: 5s\n"
            "      retries: 30\n"
            "\n"
            "  airflow-scheduler:\n"
            "    image: apache/airflow:2.10.5-python3.12\n"
            "    depends_on:\n"
            "      airflow-init:\n"
            "        condition: service_completed_successfully\n"
            + scheduler_dependencies
            + "    environment:\n"
            + environment
            + "    volumes:\n"
            + volumes
            + "    command: scheduler\n"
            "    restart: unless-stopped\n"
        )

    def _render_env(
        self,
        specification: ProjectSpec,
        *,
        postgres_mode: str,
        redis_mode: str | None,
        redis_service: ServiceSpec | None,
        has_rabbitmq: bool,
        has_durable_jobs: bool,
        has_application: bool,
        has_rag: bool,
        host_port_base: int | None,
    ) -> str:
        application_port = self._host_port(host_port_base, default=28000, offset=0)
        postgres_port = self._host_port(host_port_base, default=25432, offset=10)
        amqp_port = self._host_port(host_port_base, default=25672, offset=30)
        management_port = self._host_port(host_port_base, default=25673, offset=31)
        airflow_port = self._host_port(host_port_base, default=28080, offset=40)
        lines = [
            "# Copy to .env and replace sample credentials before sharing the file.\n",
            "LOCAL_BIND_ADDRESS=127.0.0.1\n",
        ]
        if specification.application.databases:
            lines.extend(
                [
                    "POSTGRES_USER=autoforge\n",
                    "POSTGRES_PASSWORD=change-me\n",
                    f"POSTGRES_PORT={postgres_port}\n",
                ]
            )
            if postgres_mode == "ha":
                lines.extend(
                    [
                        "POSTGRES_REPLICATION_PASSWORD=change-me-replication\n",
                        "POSTGRES_HA_SCOPE=autoforge-postgres\n",
                    ]
                )
        if redis_mode == "standalone":
            lines.append("REDIS_URL=redis://redis:6379\n")
        elif redis_mode == "cluster":
            lines.extend(
                [
                    f"{redis_service.cluster_url_env}=redis://redis-7000:7000\n",
                    f"{redis_service.cluster_startup_nodes_env}=redis://redis-7000:7000,redis://redis-7001:7001,redis://redis-7002:7002,redis://redis-7003:7003,redis://redis-7004:7004,redis://redis-7005:7005\n",
                ]
            )
        if has_rabbitmq:
            lines.extend(
                [
                    "RABBITMQ_USER=autoforge\n",
                    "RABBITMQ_PASSWORD=change-me\n",
                    f"RABBITMQ_AMQP_PORT={amqp_port}\n",
                    f"RABBITMQ_MANAGEMENT_PORT={management_port}\n",
                    "RABBITMQ_URL=amqp://autoforge:change-me@rabbitmq:5672/\n",
                ]
            )
        if has_durable_jobs:
            durable_job_api_url = (
                "http://application:8000"
                if has_application
                else "http://host.docker.internal:8000"
            )
            lines.extend(
                [
                    f"AIRFLOW_PORT={airflow_port}\n",
                    f"DURABLE_JOB_API_URL={durable_job_api_url}\n",
                    "DURABLE_JOB_API_TOKEN=change-me\n",
                ]
            )
        if has_application:
            lines.append(f"APPLICATION_PORT={application_port}\n")
        if has_rag:
            search_backend = specification.tooling.rag.search_backend
            lines.extend(
                [
                    f"RAG_NETWORK_NAME={specification.project.package_name}-rag\n",
                    f"RAG_SEARCH_BACKEND={search_backend}\n",
                    f"RAG_SEARCH_URL=http://{search_backend}:9200\n",
                    "RAG_OLLAMA_URL=http://ollama:11434\n",
                    "RAG_EMBEDDING_MODEL=embeddinggemma\n",
                ]
            )
        return "".join(lines)

    @staticmethod
    def _render_readme(
        *,
        redis_mode: str | None,
        postgres_mode: str,
        has_rabbitmq: bool,
        has_durable_jobs: bool,
        has_application: bool,
        has_migration: bool,
    ) -> str:
        services = [
            "three-node PostgreSQL HA cluster"
            if postgres_mode == "ha"
            else "PostgreSQL"
        ]
        if redis_mode == "cluster":
            services.append("three-node Redis Cluster")
        elif redis_mode == "standalone":
            services.append("Redis")
        if has_rabbitmq:
            services.append("RabbitMQ")
        if has_durable_jobs:
            services.extend(["Airflow", "Outbox relay", "durable-job worker"])
        return (
            "# Generated integration environment\n"
            "\n"
            f"This disposable profile starts {', '.join(services)} for integration checks.\n"
            "\n"
            "```powershell\n"
            "Copy-Item .env.example .env\n"
            "docker compose --env-file .env -f compose.integration.yml up -d --wait\n"
            "docker compose --env-file .env -f compose.integration.yml down\n"
            "```\n"
            "\n"
            "Long-running services use `restart: unless-stopped`, so they recover "
            "after the Docker engine restarts. The host must start Docker automatically; "
            "AWS Launch Template UserData is a separate deployment concern and is not "
            "part of this disposable integration profile.\n"
            "\n"
            "Run application containers on the Compose network. The Redis Cluster URL uses\n"
            "Docker service DNS and is intentionally not a host-process URL.\n"
            + (
                "The generated application is built from Dockerfile. "
                + (
                    "When Docker is enabled, migrations run before the generated "
                    "application starts.\n"
                    if has_migration
                    else "No database migration service is required.\n"
                )
                if has_application
                else "Enable the local application profile to generate the application service.\n"
            )
            + (
                "Airflow is generated paused and reads the durable-job API token from .env. "
                "The outbox relay and durable-job worker run from the same local image.\n"
                if has_durable_jobs
                else ""
            )
        )
