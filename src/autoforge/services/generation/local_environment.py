import json
from pathlib import PurePosixPath

import yaml

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
        local_environment = specification.tooling.local_environment
        database_provider = local_environment.database_provider
        postgres_mode = local_environment.postgres_mode
        mysql_mode = local_environment.mysql_mode
        rabbitmq_mode = local_environment.rabbitmq_mode
        airflow_scheduler_replicas = local_environment.airflow_scheduler_replicas
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
        host_port_base = local_environment.host_port_base
        database_names = self._database_names(specification.application.databases)
        if has_durable_jobs and "airflow" not in database_names:
            database_names.append("airflow")

        compose = self._render_compose(
            specification,
            database_names=database_names,
            database_provider=database_provider,
            postgres_mode=postgres_mode,
            mysql_mode=mysql_mode,
            redis_mode=redis_mode,
            redis_service=redis_service,
            has_rabbitmq=bool(rabbitmq_services),
            rabbitmq_mode=rabbitmq_mode,
            airflow_scheduler_replicas=airflow_scheduler_replicas,
            has_durable_jobs=has_durable_jobs,
            has_application=has_application,
            has_migration=has_migration,
            has_rag=has_rag,
            host_port_base=host_port_base,
        )
        files = {
            PurePosixPath("environment", "compose.integration.yml"): compose,
            PurePosixPath("environment", "service-composition.json"):
                self._render_service_composition(specification, compose),
            PurePosixPath("environment", ".env.example"): self._render_env(
                specification,
                database_provider=database_provider,
                postgres_mode=postgres_mode,
                mysql_mode=mysql_mode,
                redis_mode=redis_mode,
                redis_service=redis_service,
                has_rabbitmq=bool(rabbitmq_services),
                rabbitmq_mode=rabbitmq_mode,
                airflow_scheduler_replicas=airflow_scheduler_replicas,
                has_durable_jobs=has_durable_jobs,
                has_application=has_application,
                has_rag=has_rag,
                host_port_base=host_port_base,
            ),
            PurePosixPath("environment", "README.md"): self._render_readme(
                database_provider=database_provider,
                redis_mode=redis_mode,
                postgres_mode=postgres_mode,
                mysql_mode=mysql_mode,
                has_rabbitmq=bool(rabbitmq_services),
                rabbitmq_mode=rabbitmq_mode,
                airflow_scheduler_replicas=airflow_scheduler_replicas,
                has_durable_jobs=has_durable_jobs,
                has_application=has_application,
                has_migration=has_migration,
            ),
        }
        if database_names and database_provider == "postgresql":
            files[
                PurePosixPath("environment", "postgres-init", "00-databases.sql")
            ] = self._render_database_initialization(database_names)
        if database_provider == "postgresql" and postgres_mode == "ha" and database_names:
            files[PurePosixPath("environment", "postgres-ha", "haproxy.cfg")] = (
                self._render_postgres_ha_haproxy_config()
            )
        if database_provider == "mysql" and mysql_mode == "ha":
            files[PurePosixPath("environment", "mysql-ha", "Dockerfile.router")] = (
                self._render_mysql_router_dockerfile()
            )
            files[PurePosixPath("environment", "mysql-ha", "bootstrap.js")] = (
                self._render_mysql_ha_bootstrap()
            )
        if rabbitmq_mode == "cluster" and rabbitmq_services:
            rabbitmq_config = self._render_rabbitmq_cluster_config()
            for index in range(3):
                files[
                    PurePosixPath("environment", "rabbitmq", f"rabbitmq-{index}.conf")
                ] = rabbitmq_config
            files[PurePosixPath("environment", "rabbitmq", "haproxy.cfg")] = (
                self._render_rabbitmq_haproxy_config()
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

    @classmethod
    def _render_service_composition(
        cls,
        specification: ProjectSpec,
        compose_content: str,
    ) -> str:
        """Render a read-only service view from the generated Compose source."""
        compose = yaml.safe_load(compose_content)
        services = compose["services"]
        contract = {
            "contract_version": "1",
            "profile": "local-integration",
            "compose_file": "environment/compose.integration.yml",
            "services": [
                cls._describe_composed_service(name, services[name])
                for name in sorted(services)
            ],
            "declared_service_contracts": [
                cls._describe_declared_service(service)
                for service in specification.application.services
            ],
            "durable_jobs": [
                {
                    "name": job.name,
                    "store": job.store,
                    "event_type": job.event_type,
                    "routing_key": job.routing_key,
                    "schedule": job.schedule,
                }
                for job in specification.application.durable_jobs
            ],
        }
        return json.dumps(contract, indent=2, sort_keys=True) + "\n"

    @staticmethod
    def _describe_composed_service(name: str, definition: dict[str, object]) -> dict[str, object]:
        dependency_conditions = {
            dependency: (
                settings.get("condition", "service_started")
                if isinstance(settings, dict)
                else "service_started"
            )
            for dependency, settings in definition.get("depends_on", {}).items()
        }
        environment = definition.get("environment", {})
        restart_policy = definition.get("restart", "no")
        return {
            "name": name,
            "role": LocalEnvironmentGenerator._service_role(name),
            "lifecycle": "one_shot" if restart_policy == "no" else "long_running",
            "restart_policy": restart_policy,
            "healthcheck": "healthcheck" in definition,
            "dependencies": dependency_conditions,
            "configuration_env": sorted(environment) if isinstance(environment, dict) else [],
            "published_ports": definition.get("ports", []),
        }

    @staticmethod
    def _service_role(name: str) -> str:
        """Expose the generated runtime role without changing service names."""

        if name == "application":
            return "api"
        if name == "outbox-relay":
            return "relay"
        if name in {"message-worker", "durable-job-worker"}:
            return "worker"
        if name.startswith("airflow-"):
            return "scheduler"
        if name in {"migrate", "airflow-init", "postgres-ha-init", "mysql-init", "mysql-router-bootstrap"}:
            return "initializer"
        return "infrastructure"

    @staticmethod
    def _describe_declared_service(service: ServiceSpec) -> dict[str, object]:
        if service.kind == "redis_session":
            connection_env = {
                "standalone": [service.url_env],
                "cluster": [service.cluster_url_env, service.cluster_startup_nodes_env],
                "sentinel": [service.sentinel_urls_env],
            }[service.mode]
            return {
                "name": service.name,
                "kind": service.kind,
                "mode": service.mode,
                "configuration_env": connection_env,
            }
        return {
            "name": service.name,
            "kind": service.kind,
            "configuration_env": [service.connection_url_env],
            "event_queue": {
                "exchange": service.exchange,
                "queue": service.queue,
                "routing_key": service.routing_key,
                "dead_letter_exchange": service.dead_letter_exchange,
                "dead_letter_queue": service.dead_letter_queue,
                "queue_type": service.queue_type,
                "outbox_stores": service.outbox_stores,
            },
        }

    def _render_compose(
        self,
        specification: ProjectSpec,
        *,
        database_names: list[str],
        database_provider: str,
        postgres_mode: str,
        mysql_mode: str,
        redis_mode: str | None,
        redis_service: ServiceSpec | None,
        has_rabbitmq: bool,
        rabbitmq_mode: str,
        airflow_scheduler_replicas: int,
        has_durable_jobs: bool,
        has_application: bool,
        has_migration: bool,
        has_rag: bool,
        host_port_base: int | None,
    ) -> str:
        services: list[str] = []
        if specification.application.databases:
            if database_provider == "mysql":
                services.extend(
                    self._render_mysql_ha(host_port_base)
                    if mysql_mode == "ha"
                    else [self._render_mysql(host_port_base)]
                )
                services.append(
                    self._render_mysql_init(database_names, mysql_mode=mysql_mode)
                )
            elif postgres_mode == "ha":
                services.extend(self._render_postgres_ha(database_names, host_port_base))
            else:
                services.append(self._render_postgres(host_port_base))
        if redis_mode == "standalone":
            services.append(self._render_redis_standalone())
        elif redis_mode == "cluster":
            services.extend(self._render_redis_cluster())
        if has_rabbitmq:
            services.extend(self._render_rabbitmq(rabbitmq_mode, host_port_base))
        if has_application:
            if has_migration:
                services.append(
                    self._render_migrate(
                        specification,
                        database_provider=database_provider,
                        postgres_mode=postgres_mode,
                    )
                )
            services.append(
                self._render_application(
                    specification,
                    redis_mode=redis_mode,
                    redis_service=redis_service,
                    has_migration=has_migration,
                    has_rag=has_rag,
                    host_port_base=host_port_base,
                )
            )
            if has_rabbitmq:
                services.append(
                    self._render_outbox_relay(
                        specification, has_migration=has_migration
                    )
                )
                services.append(
                    self._render_message_worker(
                        specification, has_migration=has_migration
                    )
                )
            if has_durable_jobs:
                services.append(
                    self._render_durable_job_worker(
                        specification, has_rag=has_rag
                    )
                )
        if has_durable_jobs:
            services.append(
                self._render_airflow(
                    durable_job_token_env=specification.application.service_token_environments[
                        "durable_jobs"
                    ],
                    has_application=has_application,
                    postgres_mode=postgres_mode,
                    scheduler_replicas=airflow_scheduler_replicas,
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
                database_provider=database_provider,
                postgres_mode=postgres_mode,
                mysql_mode=mysql_mode,
                redis_mode=redis_mode,
                has_rabbitmq=has_rabbitmq,
                rabbitmq_mode=rabbitmq_mode,
                has_durable_jobs=has_durable_jobs,
            )
        )

    @staticmethod
    def _render_volumes(
        *,
        database_provider: str,
        postgres_mode: str,
        mysql_mode: str,
        redis_mode: str | None,
        has_rabbitmq: bool,
        rabbitmq_mode: str,
        has_durable_jobs: bool,
    ) -> str:
        names = (
            [f"postgres-ha-{index}-data" for index in range(3)]
            + [f"etcd-{index}-data" for index in range(3)]
            if postgres_mode == "ha"
            else []
        ) + (
            ([f"mysql-ha-{index}-data" for index in range(3)] + ["mysql-router-data"])
            if database_provider == "mysql" and mysql_mode == "ha"
            else ["mysql-data"] if database_provider == "mysql" else []
        ) + (
            [f"redis-{port}-data" for port in range(7000, 7006)]
            if redis_mode == "cluster"
            else []
        )
        if has_rabbitmq:
            names.extend(
                [f"rabbitmq-{index}-data" for index in range(3)]
                if rabbitmq_mode == "cluster"
                else ["rabbitmq-data"]
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
    def _render_mysql(cls, host_port_base: int | None) -> str:
        mysql_port = cls._host_port(host_port_base, default=23306, offset=10)
        return (
            "  mysql:\n"
            "    image: mysql:8.4\n"
            "    restart: unless-stopped\n"
            "    environment:\n"
            "      MYSQL_USER: ${MYSQL_USER:-autoforge}\n"
            "      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-change-me}\n"
            "      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-change-me-root}\n"
            "    ports:\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{MYSQL_PORT:-{mysql_port}}}:3306\"\n"
            "    volumes:\n"
            "      - mysql-data:/var/lib/mysql\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"mysqladmin ping -h 127.0.0.1 -uroot -p$$MYSQL_ROOT_PASSWORD --silent\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )

    @staticmethod
    def _render_mysql_init(database_names: list[str], *, mysql_mode: str) -> str:
        mysql_port = 6446 if mysql_mode == "ha" else 3306
        statements = (
            "CREATE USER IF NOT EXISTS '$$MYSQL_USER'@'%' "
            "IDENTIFIED BY '$$MYSQL_PASSWORD'; "
            + " ".join(
            (
                f"CREATE DATABASE IF NOT EXISTS {database_name}; "
                f"GRANT ALL PRIVILEGES ON {database_name}.* "
                "TO '$$MYSQL_USER'@'%';"
            )
            for database_name in database_names
            )
        )
        return (
            "  mysql-init:\n"
            "    image: mysql:8.4\n"
            "    depends_on:\n"
            "      mysql:\n"
            "        condition: service_healthy\n"
            "    environment:\n"
            "      MYSQL_USER: ${MYSQL_USER:-autoforge}\n"
            "      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-change-me}\n"
            "      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-change-me-root}\n"
            "    command:\n"
            "      - /bin/sh\n"
            "      - -ec\n"
            "      - |\n"
            f"        mysql -hmysql -P {mysql_port} -uroot -p\"$$MYSQL_ROOT_PASSWORD\" -e \""
            + statements
            + "\"\n"
            "    restart: \"no\"\n"
        )

    @classmethod
    def _render_mysql_ha(cls, host_port_base: int | None) -> list[str]:
        mysql_port = cls._host_port(host_port_base, default=23306, offset=10)
        return [
            *(cls._render_mysql_ha_node(index) for index in range(3)),
            (
            "  mysql-cluster-init:\n"
            "    image: mysql:8.4\n"
            "    depends_on:\n"
            "      mysql-ha-0:\n        condition: service_healthy\n"
            "      mysql-ha-1:\n        condition: service_healthy\n"
            "      mysql-ha-2:\n        condition: service_healthy\n"
            "    environment:\n"
            "      MYSQL_CLUSTER_ADMIN_USER: ${MYSQL_CLUSTER_ADMIN_USER:-autoforge_cluster}\n"
            "      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-change-me-root}\n"
            "      MYSQL_CLUSTER_ADMIN_PASSWORD: ${MYSQL_CLUSTER_ADMIN_PASSWORD:-change-me-cluster}\n"
            "    volumes:\n"
            "      - ./mysql-ha/bootstrap.js:/scripts/bootstrap.js:ro\n"
            "    command:\n"
            "      - /bin/sh\n      - -ec\n"
            "      - exec mysqlsh --no-wizard --js --uri \"root:$$MYSQL_ROOT_PASSWORD@mysql-ha-0:3306\" --file /scripts/bootstrap.js\n"
            "    restart: \"no\"\n"
            ),
            (
            "  mysql-router-bootstrap:\n"
            "    build:\n      context: ./mysql-ha\n      dockerfile: Dockerfile.router\n"
            "      args:\n        MYSQL_ROUTER_VERSION: ${MYSQL_ROUTER_VERSION:-8.4.8}\n"
            "    depends_on:\n      mysql-cluster-init:\n        condition: service_completed_successfully\n"
            "    command:\n"
            "      - --bootstrap\n"
            "      - ${MYSQL_CLUSTER_ADMIN_USER:-autoforge_cluster}:${MYSQL_CLUSTER_ADMIN_PASSWORD:-change-me-cluster}@mysql-ha-0:3306\n"
            "      - --directory\n      - /router\n      - --user\n      - mysqlrouter\n      - --force\n"
            "    volumes:\n      - mysql-router-data:/router\n"
            "    restart: \"no\"\n"
            ),
            (
            "  mysql:\n"
            "    build:\n      context: ./mysql-ha\n      dockerfile: Dockerfile.router\n"
            "      args:\n        MYSQL_ROUTER_VERSION: ${MYSQL_ROUTER_VERSION:-8.4.8}\n"
            "    user: mysqlrouter\n"
            "    restart: unless-stopped\n"
            "    depends_on:\n      mysql-router-bootstrap:\n        condition: service_completed_successfully\n"
            "    environment:\n"
            "      MYSQL_CLUSTER_ADMIN_USER: ${MYSQL_CLUSTER_ADMIN_USER:-autoforge_cluster}\n"
            "      MYSQL_CLUSTER_ADMIN_PASSWORD: ${MYSQL_CLUSTER_ADMIN_PASSWORD:-change-me-cluster}\n"
            "    command: [\"-c\", \"/router/mysqlrouter.conf\"]\n"
            "    ports:\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{MYSQL_PORT:-{mysql_port}}}:6446\"\n"
            "    volumes:\n      - mysql-router-data:/router\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"mysqladmin ping -h 127.0.0.1 -P 6446 -u$$MYSQL_CLUSTER_ADMIN_USER -p$$MYSQL_CLUSTER_ADMIN_PASSWORD --silent\"]\n"
            "      interval: 3s\n      timeout: 3s\n      retries: 30\n"
            ),
        ]

    @staticmethod
    def _render_mysql_ha_node(index: int) -> str:
        return (
            f"  mysql-ha-{index}:\n"
            "    image: mysql:8.4\n"
            "    restart: unless-stopped\n"
            "    command:\n"
            f"      - --server-id={100 + index}\n"
            f"      - --report-host=mysql-ha-{index}\n"
            "      - --skip-name-resolve\n      - --binlog-checksum=NONE\n"
            "      - --enforce-gtid-consistency=ON\n      - --gtid-mode=ON\n"
            "      - --log-bin=mysql-bin\n      - --log-replica-updates=ON\n"
            "    environment:\n"
            "      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-change-me-root}\n"
            "      MYSQL_ROOT_HOST: \"%\"\n"
            "    volumes:\n"
            f"      - mysql-ha-{index}-data:/var/lib/mysql\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"mysqladmin ping -h 127.0.0.1 -uroot -p$$MYSQL_ROOT_PASSWORD --silent\"]\n"
            "      interval: 3s\n      timeout: 3s\n      retries: 30\n"
        )

    @staticmethod
    def _render_mysql_router_dockerfile() -> str:
        return (
            "FROM mysql:8.4\n\n"
            "ARG MYSQL_ROUTER_VERSION=8.4.8\n"
            "RUN rpm --import https://repo.mysql.com/RPM-GPG-KEY-mysql-2023 \\\n"
            "    && curl -fsSLo /tmp/mysql-router.rpm \\\n"
            "      \"https://repo.mysql.com/yum/mysql-tools-8.4-community/el/9/x86_64/mysql-router-community-${MYSQL_ROUTER_VERSION}-1.el9.x86_64.rpm\" \\\n"
            "    && rpm -ivh /tmp/mysql-router.rpm \\\n"
            "    && rm -f /tmp/mysql-router.rpm\n\n"
            "ENTRYPOINT [\"mysqlrouter\"]\n"
        )

    @staticmethod
    def _render_mysql_ha_bootstrap() -> str:
        return (
            "const rootPassword = os.getenv(\"MYSQL_ROOT_PASSWORD\");\n"
            "const clusterAdmin = os.getenv(\"MYSQL_CLUSTER_ADMIN_USER\") || \"autoforge_cluster\";\n"
            "const clusterPassword = os.getenv(\"MYSQL_CLUSTER_ADMIN_PASSWORD\");\n"
            "const instances = [\"mysql-ha-0\", \"mysql-ha-1\", \"mysql-ha-2\"];\n"
            "const rootUri = (host) => `root:${rootPassword}@${host}:3306`;\n"
            "const adminUri = (host) => `${clusterAdmin}:${clusterPassword}@${host}:3306`;\n\n"
            "let cluster;\n"
            "try {\n  shell.connect(adminUri(\"mysql-ha-0\"));\n  cluster = dba.getCluster();\n"
            "} catch (error) {\n"
            "  if (!String(error).includes(\"Access denied\") && !String(error).includes(\"does not belong to an InnoDB Cluster\")) throw error;\n"
            "  for (const host of instances) {\n"
            "    dba.configureInstance(rootUri(host), {clusterAdmin, clusterAdminPassword: clusterPassword, restart: false});\n"
            "  }\n"
            "  shell.connect(adminUri(\"mysql-ha-0\"));\n"
            "  cluster = dba.createCluster(\"autoforgeCluster\", {multiPrimary: false});\n"
            "}\n\n"
            "const topology = cluster.status().defaultReplicaSet.topology;\n"
            "for (const host of instances.slice(1)) {\n"
            "  if (!(`${host}:3306` in topology)) cluster.addInstance(adminUri(host), {recoveryMethod: \"clone\"});\n"
            "}\n"
            "print(JSON.stringify(cluster.status()));\n"
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
    def _render_rabbitmq(
        cls, rabbitmq_mode: str, host_port_base: int | None
    ) -> list[str]:
        if rabbitmq_mode == "cluster":
            return cls._render_rabbitmq_cluster(host_port_base)
        amqp_port = cls._host_port(host_port_base, default=25672, offset=30)
        management_port = cls._host_port(host_port_base, default=25673, offset=31)
        return [
            (
            "  rabbitmq:\n"
            "    image: rabbitmq:4.1-management-alpine\n"
            "    restart: unless-stopped\n"
            "    environment:\n"
            "      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-autoforge}\n"
            "      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-change-me}\n"
            "    volumes:\n"
            "      - rabbitmq-data:/var/lib/rabbitmq\n"
            "    ports:\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{RABBITMQ_AMQP_PORT:-{amqp_port}}}:5672\"\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{RABBITMQ_MANAGEMENT_PORT:-{management_port}}}:15672\"\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"rabbitmq-diagnostics -q check_port_connectivity\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
            )
        ]

    @classmethod
    def _render_rabbitmq_cluster(cls, host_port_base: int | None) -> list[str]:
        services = [cls._render_rabbitmq_node(index) for index in range(3)]
        amqp_port = cls._host_port(host_port_base, default=25672, offset=30)
        management_port = cls._host_port(host_port_base, default=25673, offset=31)
        services.append(
            "  rabbitmq:\n"
            "    image: haproxy:3.0-alpine\n"
            "    restart: unless-stopped\n"
            "    ports:\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{RABBITMQ_AMQP_PORT:-{amqp_port}}}:5672\"\n"
            f"      - \"${{LOCAL_BIND_ADDRESS:-127.0.0.1}}:${{RABBITMQ_MANAGEMENT_PORT:-{management_port}}}:15672\"\n"
            "    volumes:\n"
            "      - ./rabbitmq/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro\n"
            "    depends_on:\n"
            "      rabbitmq-0:\n"
            "        condition: service_healthy\n"
            "      rabbitmq-1:\n"
            "        condition: service_healthy\n"
            "      rabbitmq-2:\n"
            "        condition: service_healthy\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"nc -z 127.0.0.1 5672\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )
        return services

    @staticmethod
    def _render_rabbitmq_node(index: int) -> str:
        return (
            f"  rabbitmq-{index}:\n"
            "    image: rabbitmq:4.1-management-alpine\n"
            "    restart: unless-stopped\n"
            "    hostname: rabbitmq-"
            f"{index}\n"
            "    environment:\n"
            "      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-autoforge}\n"
            "      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-change-me}\n"
            "      RABBITMQ_ERLANG_COOKIE: ${RABBITMQ_ERLANG_COOKIE:?set RABBITMQ_ERLANG_COOKIE}\n"
            f"      RABBITMQ_NODENAME: rabbit@rabbitmq-{index}\n"
            "    volumes:\n"
            f"      - rabbitmq-{index}-data:/var/lib/rabbitmq\n"
            f"      - ./rabbitmq/rabbitmq-{index}.conf:/etc/rabbitmq/rabbitmq.conf:ro\n"
            + "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"rabbitmq-diagnostics -q check_port_connectivity\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )

    @staticmethod
    def _render_rabbitmq_cluster_config() -> str:
        return (
            "cluster_formation.peer_discovery_backend = classic_config\n"
            "cluster_formation.classic_config.nodes.1 = rabbit@rabbitmq-0\n"
            "cluster_formation.classic_config.nodes.2 = rabbit@rabbitmq-1\n"
            "cluster_formation.classic_config.nodes.3 = rabbit@rabbitmq-2\n"
            "cluster_partition_handling = pause_minority\n"
            "queue_leader_locator = balanced\n"
        )

    @staticmethod
    def _render_rabbitmq_haproxy_config() -> str:
        return (
            "global\n"
            "\n"
            "defaults\n"
            "  mode tcp\n"
            "  timeout connect 5s\n"
            "  timeout client 60s\n"
            "  timeout server 60s\n"
            "\n"
            "frontend rabbitmq-amqp\n"
            "  bind *:5672\n"
            "  default_backend rabbitmq-amqp-nodes\n"
            "\n"
            "backend rabbitmq-amqp-nodes\n"
            "  option tcp-check\n"
            "  server rabbitmq-0 rabbitmq-0:5672 check\n"
            "  server rabbitmq-1 rabbitmq-1:5672 check\n"
            "  server rabbitmq-2 rabbitmq-2:5672 check\n"
            "\n"
            "frontend rabbitmq-management\n"
            "  bind *:15672\n"
            "  default_backend rabbitmq-management-nodes\n"
            "\n"
            "backend rabbitmq-management-nodes\n"
            "  option tcp-check\n"
            "  server rabbitmq-0 rabbitmq-0:15672 check\n"
            "  server rabbitmq-1 rabbitmq-1:15672 check\n"
            "  server rabbitmq-2 rabbitmq-2:15672 check\n"
        )

    @staticmethod
    def _render_database_environment(specification: ProjectSpec) -> str:
        database_provider = specification.tooling.local_environment.database_provider
        if database_provider == "mysql":
            mysql_port = (
                6446
                if specification.tooling.local_environment.mysql_mode == "ha"
                else 3306
            )
            url = (
                "mysql+asyncmy://${MYSQL_USER:-autoforge}:${MYSQL_PASSWORD:-change-me}"
                f"@mysql:{mysql_port}/{{database_name}}?charset=utf8mb4"
            )
        else:
            url = (
                "postgresql+asyncpg://${POSTGRES_USER:-autoforge}:"
                "${POSTGRES_PASSWORD:-change-me}@postgres:5432/{database_name}"
            )
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
                        f"{environment_name}: {url.replace('{database_name}', database_name)}\n"
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

    def _render_migrate(
        self,
        specification: ProjectSpec,
        *,
        database_provider: str,
        postgres_mode: str,
    ) -> str:
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
                "      mysql-init:\n        condition: service_completed_successfully\n"
                if database_provider == "mysql"
                else (
                "      postgres-ha-init:\n"
                "        condition: service_completed_successfully\n"
                if postgres_mode == "ha"
                else "      postgres:\n        condition: service_healthy\n"
                )
            )
            + "    restart: \"no\"\n"
        )

    def _render_application(
        self,
        specification: ProjectSpec,
        *,
        redis_mode: str | None,
        redis_service: ServiceSpec | None,
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
        service_token_environment = self._render_service_token_environment(
            specification
        )
        heartbeat_environment = ""
        heartbeat = specification.application.control_plane_heartbeat
        if heartbeat.enabled:
            heartbeat_environment = (
                f"      {heartbeat.endpoint_env}: ${{{heartbeat.endpoint_env}:-}}\n"
                f"      {heartbeat.token_env}: ${{{heartbeat.token_env}:-}}\n"
            )
        rag_environment = self._render_rag_environment(specification) if has_rag else ""
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
            + service_token_environment
            + heartbeat_environment
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
            '"from urllib.request import urlopen; urlopen(\'http://127.0.0.1:8000/readiness\').read()"]\n'
            "      interval: 5s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )

    @staticmethod
    def _render_service_token_environment(specification: ProjectSpec) -> str:
        return "".join(
            f"      {token_env}: ${{{token_env}:?set {token_env}}}\n"
            for _, token_env in sorted(
                specification.application.service_token_environments.items()
            )
        )

    def _render_outbox_relay(
        self, specification: ProjectSpec, *, has_migration: bool
    ) -> str:
        image = self._application_image(specification)
        migration_dependency = (
            "      migrate:\n"
            "        condition: service_completed_successfully\n"
            if has_migration
            else ""
        )
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
            + migration_dependency
            + "      rabbitmq:\n"
            + "        condition: service_healthy\n"
        )

    def _render_message_worker(
        self, specification: ProjectSpec, *, has_migration: bool
    ) -> str:
        image = self._application_image(specification)
        migration_dependency = (
            "      migrate:\n"
            "        condition: service_completed_successfully\n"
            if has_migration
            else ""
        )
        return (
            "  message-worker:\n"
            f"    image: ${{APPLICATION_IMAGE:-{image}}}\n"
            "    pull_policy: never\n"
            "    restart: unless-stopped\n"
            "    command: [\"python\", \"scripts/run_message_worker.py\"]\n"
            "    healthcheck:\n"
            '      test: ["CMD", "python", "-c", "import asyncio, os, aio_pika; connection = asyncio.run(aio_pika.connect(os.environ[\'RABBITMQ_URL\'], timeout=2)); asyncio.run(connection.close())"]\n'
            "      interval: 10s\n"
            "      timeout: 3s\n"
            "      retries: 3\n"
            "    environment:\n"
            + self._render_database_environment(specification)
            + "      RABBITMQ_URL: ${RABBITMQ_URL:?set RABBITMQ_URL}\n"
            "    depends_on:\n"
            + migration_dependency
            + "      rabbitmq:\n"
            + "        condition: service_healthy\n"
        )

    def _render_durable_job_worker(
        self, specification: ProjectSpec, *, has_rag: bool
    ) -> str:
        image = self._application_image(specification)
        restart_policy = specification.application.durable_job_worker_restart_policy
        heartbeat = specification.application.control_plane_heartbeat
        heartbeat_environment = (
            f"      {heartbeat.endpoint_env}: ${{{heartbeat.endpoint_env}:-}}\n"
            f"      {heartbeat.token_env}: ${{{heartbeat.token_env}:-}}\n"
            if heartbeat.enabled
            else ""
        )
        rag_network = "    networks:\n      - default\n      - rag\n" if has_rag else ""
        rag_environment = self._render_rag_environment(specification) if has_rag else ""
        rag_healthcheck = (
            "; from urllib.request import urlopen; "
            "urlopen(os.environ['RAG_SEARCH_URL'] + '/_cluster/health', timeout=2).read(); "
            "urlopen(os.environ['RAG_OLLAMA_URL'] + '/api/tags', timeout=2).read()"
            if has_rag
            else ""
        )
        return (
            "  durable-job-worker:\n"
            f"    image: ${{APPLICATION_IMAGE:-{image}}}\n"
            "    pull_policy: never\n"
            f'    restart: "{restart_policy}"\n'
            "    command: [\"python\", \"scripts/run_durable_job_worker.py\"]\n"
            "    healthcheck:\n"
            '      test: ["CMD", "python", "-c", "import asyncio, os, aio_pika; connection = asyncio.run(aio_pika.connect(os.environ[\'RABBITMQ_URL\'], timeout=2)); asyncio.run(connection.close())'
            + rag_healthcheck
            + '"]\n'
            "      interval: 10s\n"
            "      timeout: 3s\n"
            "      retries: 3\n"
            "    environment:\n"
            + self._render_database_environment(specification)
            + "      RABBITMQ_URL: ${RABBITMQ_URL:?set RABBITMQ_URL}\n"
            + heartbeat_environment
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
        cls,
        *,
        durable_job_token_env: str,
        has_application: bool,
        postgres_mode: str,
        scheduler_replicas: int,
        host_port_base: int | None,
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
        scheduler_ha_environment = (
            "      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY:?set AIRFLOW_FERNET_KEY}\n"
            "      AIRFLOW__SCHEDULER__ENABLE_HEALTH_CHECK: \"true\"\n"
            "      AIRFLOW__SCHEDULER__FILE_PARSING_SORT_MODE: random_seeded_by_host\n"
            "      AIRFLOW__SCHEDULER__USE_ROW_LEVEL_LOCKING: \"true\"\n"
            if scheduler_replicas > 1
            else ""
        )
        environment = (
            f"      AIRFLOW__CORE__EXECUTOR: {'LocalExecutor' if scheduler_replicas > 1 else 'SequentialExecutor'}\n"
            "      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER:-autoforge}:${POSTGRES_PASSWORD:-change-me}@postgres:5432/airflow\n"
            "      AIRFLOW__CORE__LOAD_EXAMPLES: \"false\"\n"
            "      AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: \"true\"\n"
            + scheduler_ha_environment
            + f"      DURABLE_JOB_API_URL: ${{DURABLE_JOB_API_URL:-{api_url}}}\n"
            + f"      {durable_job_token_env}: ${{{durable_job_token_env}:?set {durable_job_token_env}}}\n"
        )
        volumes = (
            "      - ../airflow/dags:/opt/airflow/dags:ro\n"
            "      - airflow-home:/opt/airflow\n"
        )
        scheduler_names = (
            ["airflow-scheduler"]
            if scheduler_replicas == 1
            else [f"airflow-scheduler-{index}" for index in range(scheduler_replicas)]
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
            "    command: webserver --pid /tmp/airflow-webserver.pid\n"
            "    restart: unless-stopped\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"curl --fail http://localhost:8080/health || exit 1\"]\n"
            "      interval: 10s\n"
            "      timeout: 5s\n"
            "      retries: 30\n"
            "\n\n"
            + "\n\n".join(
                cls._render_airflow_scheduler(
                    name=name,
                    scheduler_dependencies=scheduler_dependencies,
                    environment=environment,
                    volumes=volumes,
                    healthcheck=scheduler_replicas > 1,
                )
                for name in scheduler_names
            )
        )

    @staticmethod
    def _render_airflow_scheduler(
        *,
        name: str,
        scheduler_dependencies: str,
        environment: str,
        volumes: str,
        healthcheck: bool,
    ) -> str:
        return (
            f"  {name}:\n"
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
            + (
                "    healthcheck:\n"
                "      test: [\"CMD-SHELL\", \"curl --fail http://127.0.0.1:8974/health || exit 1\"]\n"
                "      interval: 10s\n"
                "      timeout: 5s\n"
                "      retries: 30\n"
                if healthcheck
                else ""
            )
        )

    def _render_env(
        self,
        specification: ProjectSpec,
        *,
        database_provider: str,
        postgres_mode: str,
        mysql_mode: str,
        redis_mode: str | None,
        redis_service: ServiceSpec | None,
        has_rabbitmq: bool,
        rabbitmq_mode: str,
        airflow_scheduler_replicas: int,
        has_durable_jobs: bool,
        has_application: bool,
        has_rag: bool,
        host_port_base: int | None,
    ) -> str:
        application_port = self._host_port(host_port_base, default=28000, offset=0)
        database_port = self._host_port(
            host_port_base,
            default=23306 if database_provider == "mysql" else 25432,
            offset=10,
        )
        amqp_port = self._host_port(host_port_base, default=25672, offset=30)
        management_port = self._host_port(host_port_base, default=25673, offset=31)
        airflow_port = self._host_port(host_port_base, default=28080, offset=40)
        lines = [
            "# Copy to .env and replace sample credentials before sharing the file.\n",
            "LOCAL_BIND_ADDRESS=127.0.0.1\n",
        ]
        if specification.application.databases:
            if database_provider == "mysql":
                lines.extend(
                    [
                        "MYSQL_USER=autoforge\n",
                        "MYSQL_PASSWORD=change-me\n",
                        "MYSQL_ROOT_PASSWORD=change-me-root\n",
                        *(
                            [
                                "MYSQL_CLUSTER_ADMIN_USER=autoforge_cluster\n",
                                "MYSQL_CLUSTER_ADMIN_PASSWORD=change-me-cluster\n",
                                "MYSQL_ROUTER_VERSION=8.4.8\n",
                            ]
                            if mysql_mode == "ha"
                            else []
                        ),
                        f"MYSQL_PORT={database_port}\n",
                    ]
                )
            else:
                lines.extend(
                    [
                        "POSTGRES_USER=autoforge\n",
                        "POSTGRES_PASSWORD=change-me\n",
                        f"POSTGRES_PORT={database_port}\n",
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
                    *(
                        ["RABBITMQ_ERLANG_COOKIE=replace-with-a-long-random-secret\n"]
                        if rabbitmq_mode == "cluster"
                        else []
                    ),
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
                    *(
                        [
                            "AIRFLOW_FERNET_KEY=replace-with-a-valid-fernet-key\n"
                        ]
                        if airflow_scheduler_replicas > 1
                        else []
                    ),
                    f"DURABLE_JOB_API_URL={durable_job_api_url}\n",
                ]
            )
        lines.extend(
            f"{token_env}=change-me\n"
            for _, token_env in sorted(
                specification.application.service_token_environments.items()
            )
        )
        if has_application:
            lines.append(f"APPLICATION_PORT={application_port}\n")
        heartbeat = specification.application.control_plane_heartbeat
        if heartbeat.enabled and has_application:
            lines.extend(
                [
                    f"{heartbeat.endpoint_env}=\n",
                    f"{heartbeat.token_env}=\n",
                ]
            )
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
        database_provider: str,
        redis_mode: str | None,
        postgres_mode: str,
        mysql_mode: str,
        has_rabbitmq: bool,
        rabbitmq_mode: str,
        airflow_scheduler_replicas: int,
        has_durable_jobs: bool,
        has_application: bool,
        has_migration: bool,
    ) -> str:
        services = [
            "three-node MySQL InnoDB Cluster"
            if database_provider == "mysql" and mysql_mode == "ha"
            else "MySQL"
            if database_provider == "mysql"
            else (
                "three-node PostgreSQL HA cluster"
                if postgres_mode == "ha"
                else "PostgreSQL"
            )
        ]
        if redis_mode == "cluster":
            services.append("three-node Redis Cluster")
        elif redis_mode == "standalone":
            services.append("Redis")
        if has_rabbitmq:
            services.append(
                "three-node RabbitMQ cluster" if rabbitmq_mode == "cluster" else "RabbitMQ"
            )
        if has_rabbitmq and has_application:
            services.extend(["Outbox relay", "message worker"])
        if has_durable_jobs:
            services.extend(["Airflow", "durable-job worker"])
        startup_command = (
            "docker compose --env-file .env -f compose.integration.yml up -d"
            if database_provider == "mysql"
            else "docker compose --env-file .env -f compose.integration.yml up -d --wait"
        )
        return (
            "# Generated integration environment\n"
            "\n"
            f"This disposable profile starts {', '.join(services)} for integration checks.\n"
            "\n"
            "```powershell\n"
            "Copy-Item .env.example .env\n"
            f"{startup_command}\n"
            "docker compose --env-file .env -f compose.integration.yml down\n"
            "```\n"
            "\n"
            "Long-running services use `restart: unless-stopped`, so they recover "
            "after the Docker engine restarts. The host must start Docker automatically; "
            "AWS Launch Template UserData is a separate deployment concern and is not "
            "part of this disposable integration profile.\n"
            "\n"
            + (
                "MySQL uses a one-shot `mysql-init` service to create declared databases "
                "and grant the generated application user access. Confirm it exited with code 0 "
                "using `docker compose ps` before investigating application startup.\n"
                if database_provider == "mysql"
                else ""
            )
            + (
                "RabbitMQ cluster mode keeps the existing `rabbitmq:5672` client endpoint "
                "behind HAProxy and requires a shared `RABBITMQ_ERLANG_COOKIE`. It validates "
                "container-node recovery only because all nodes share one Docker host.\n"
                "\n"
                if has_rabbitmq and rabbitmq_mode == "cluster"
                else ""
            )
            + "Run application containers on the Compose network. The Redis Cluster URL uses\n"
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
                "The durable-job worker runs from the same local image.\n"
                if has_durable_jobs
                else ""
            )
            + (
                "The outbox relay and scaffolded message worker run from the same local image. "
                "Customize the scaffolded worker handler for application event consumption.\n"
                if has_rabbitmq and has_application
                else ""
            )
            + (
                "Airflow scheduler HA uses LocalExecutor and shared PostgreSQL metadata. "
                "Set a valid shared AIRFLOW_FERNET_KEY before starting the profile; this "
                "validates scheduler-process recovery only on one Docker host.\n"
                if has_durable_jobs and airflow_scheduler_replicas > 1
                else ""
            )
        )
