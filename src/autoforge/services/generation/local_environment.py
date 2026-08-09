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
        rabbitmq_services = [
            service
            for service in specification.application.services
            if service.kind == "rabbitmq"
        ]
        if len(rabbitmq_services) > 1:
            raise ValueError("local environment supports one RabbitMQ service")
        if not specification.application.databases and redis_mode is None and not rabbitmq_services:
            raise ValueError("local environment requires a declared database or service")

        files = {
            PurePosixPath("environment", "compose.integration.yml"): self._render_compose(
                specification,
                redis_mode=redis_mode,
                has_rabbitmq=bool(rabbitmq_services),
            ),
            PurePosixPath("environment", ".env.example"): self._render_env(
                specification,
                redis_mode=redis_mode,
                has_rabbitmq=bool(rabbitmq_services),
            ),
            PurePosixPath("environment", "README.md"): self._render_readme(
                redis_mode=redis_mode,
                has_rabbitmq=bool(rabbitmq_services),
            ),
        }
        database_names = self._database_names(specification.application.databases)
        if database_names:
            files[
                PurePosixPath("environment", "postgres-init", "00-databases.sql")
            ] = "".join(f'CREATE DATABASE "{name}";\n' for name in database_names)
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
        redis_mode: str | None,
        has_rabbitmq: bool,
    ) -> str:
        services: list[str] = []
        if specification.application.databases:
            services.append(self._render_postgres())
        if redis_mode == "standalone":
            services.append(self._render_redis_standalone())
        elif redis_mode == "cluster":
            services.extend(self._render_redis_cluster())
        if has_rabbitmq:
            services.append(self._render_rabbitmq())
        return (
            f"name: {specification.project.package_name}-integration\n"
            "\n"
            "services:\n"
            + "\n".join(services)
        )

    @staticmethod
    def _render_postgres() -> str:
        return (
            "  postgres:\n"
            "    image: postgres:16-alpine\n"
            "    environment:\n"
            "      POSTGRES_USER: ${POSTGRES_USER:-autoforge}\n"
            "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change-me}\n"
            "      POSTGRES_DB: postgres\n"
            "    ports:\n"
            "      - \"${POSTGRES_PORT:-25432}:5432\"\n"
            "    volumes:\n"
            "      - ./postgres-init/00-databases.sql:/docker-entrypoint-initdb.d/00-databases.sql:ro\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"pg_isready -U $$POSTGRES_USER -d postgres\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )

    @staticmethod
    def _render_redis_standalone() -> str:
        return (
            "  redis:\n"
            "    image: redis:7-alpine\n"
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
                "    command:\n"
                "      - redis-server\n"
                f"      - --port\n      - \"{port}\"\n"
                "      - --cluster-enabled\n      - yes\n"
                "      - --cluster-config-file\n      - nodes.conf\n"
                "      - --cluster-node-timeout\n      - \"5000\"\n"
                "      - --appendonly\n      - no\n"
                "    healthcheck:\n"
                f"      test: [\"CMD-SHELL\", \"redis-cli -p {port} ping | grep -q PONG\"]\n"
                "      interval: 3s\n"
                "      timeout: 3s\n"
                "      retries: 20\n"
            )
            for port in (7000, 7001, 7002)
        ]
        nodes.append(
            "  redis-cluster-init:\n"
            "    image: redis:7-alpine\n"
            "    depends_on:\n"
            "      redis-7000:\n"
            "        condition: service_healthy\n"
            "      redis-7001:\n"
            "        condition: service_healthy\n"
            "      redis-7002:\n"
            "        condition: service_healthy\n"
            "    command:\n"
            "      - /bin/sh\n"
            "      - -c\n"
            "      - >\n"
            "        redis-cli -h redis-7000 -p 7000 cluster info | grep -q 'cluster_state:ok' ||\n"
            "        redis-cli --cluster create redis-7000:7000 redis-7001:7001 redis-7002:7002\n"
            "        --cluster-replicas 0 --cluster-yes\n"
            "    restart: \"no\"\n"
        )
        return nodes

    @staticmethod
    def _render_rabbitmq() -> str:
        return (
            "  rabbitmq:\n"
            "    image: rabbitmq:4.1-management-alpine\n"
            "    environment:\n"
            "      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-autoforge}\n"
            "      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-change-me}\n"
            "    ports:\n"
            "      - \"${RABBITMQ_AMQP_PORT:-25672}:5672\"\n"
            "      - \"${RABBITMQ_MANAGEMENT_PORT:-25673}:15672\"\n"
            "    healthcheck:\n"
            "      test: [\"CMD-SHELL\", \"rabbitmq-diagnostics -q ping\"]\n"
            "      interval: 3s\n"
            "      timeout: 3s\n"
            "      retries: 20\n"
        )

    def _render_env(
        self,
        specification: ProjectSpec,
        *,
        redis_mode: str | None,
        has_rabbitmq: bool,
    ) -> str:
        lines = [
            "# Copy to .env and replace sample credentials before sharing the file.\n",
        ]
        if specification.application.databases:
            lines.extend(
                [
                    "POSTGRES_USER=autoforge\n",
                    "POSTGRES_PASSWORD=change-me\n",
                    "POSTGRES_PORT=25432\n",
                ]
            )
        if redis_mode == "standalone":
            lines.append("REDIS_URL=redis://redis:6379\n")
        elif redis_mode == "cluster":
            lines.append("REDIS_CLUSTER_URL=redis://redis-7000:7000\n")
        if has_rabbitmq:
            lines.extend(
                [
                    "RABBITMQ_USER=autoforge\n",
                    "RABBITMQ_PASSWORD=change-me\n",
                    "RABBITMQ_AMQP_PORT=25672\n",
                    "RABBITMQ_MANAGEMENT_PORT=25673\n",
                    "RABBITMQ_URL=amqp://autoforge:change-me@rabbitmq:5672/\n",
                ]
            )
        return "".join(lines)

    @staticmethod
    def _render_readme(*, redis_mode: str | None, has_rabbitmq: bool) -> str:
        services = ["PostgreSQL"]
        if redis_mode == "cluster":
            services.append("three-node Redis Cluster")
        elif redis_mode == "standalone":
            services.append("Redis")
        if has_rabbitmq:
            services.append("RabbitMQ")
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
            "Run application containers on the Compose network. The Redis Cluster URL uses\n"
            "Docker service DNS and is intentionally not a host-process URL. Airflow, the\n"
            "application container, and message workers are separate later contracts.\n"
        )
