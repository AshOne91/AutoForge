from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from autoforge.core.specification.naming import (
    validate_class_name,
    validate_http_path,
    validate_python_name,
    validate_semantic_version,
)
from autoforge.core.specification.types import FieldType, FieldTypeKind
from autoforge.core.workspace import validate_workspace_relative_path


class StrictSpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class EndpointDependency(StrEnum):
    SESSION_STORE = "session_store"
    CURRENT_SESSION = "current_session"
    DATABASE_SESSION_REGISTRY = "database_session_registry"


class EndpointAccessLevel(StrEnum):
    USER = "user"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    ADMINISTRATOR = "administrator"


class ProjectInfo(StrictSpecModel):
    name: str = Field(min_length=1, max_length=100)
    package_name: str
    version: str
    description: str = ""
    dependencies: list[str] = Field(default_factory=list)

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        return validate_semantic_version(value)

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, values: list[str]) -> list[str]:
        if any(not value for value in values):
            raise ValueError("Project dependencies must not be empty")
        if len(values) != len(set(values)):
            raise ValueError("Project dependencies must be unique")
        return values


class ServiceSpec(StrictSpecModel):
    name: str
    kind: Literal["redis_session", "rabbitmq"]
    namespace: str = ""
    ttl_seconds: int = 0
    url_env: str = Field(default="REDIS_URL", pattern=r"^[A-Z][A-Z0-9_]*$")
    mode: Literal["standalone", "sentinel", "cluster"] = "standalone"
    cluster_url_env: str = Field(
        default="REDIS_CLUSTER_URL",
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )
    cluster_startup_nodes_env: str = Field(
        default="REDIS_CLUSTER_STARTUP_NODES",
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )
    sentinel_urls_env: str = Field(
        default="REDIS_SENTINEL_URLS",
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )
    sentinel_master: str = "session-primary"
    connection_url_env: str = Field(
        default="RABBITMQ_URL",
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )
    exchange: str = "domain.events"
    queue: str = "domain.events.worker"
    routing_key: str = "domain.#"
    dead_letter_exchange: str = "domain.events.dlx"
    dead_letter_queue: str = "domain.events.dead-letter"
    queue_type: Literal["classic", "quorum"] = "classic"
    prefetch_count: int = Field(default=32, gt=0)
    outbox_stores: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, value: str) -> str:
        return validate_python_name(value) if value else value

    @field_validator("outbox_stores")
    @classmethod
    def validate_outbox_stores(cls, values: list[str]) -> list[str]:
        validated = [validate_python_name(value) for value in values]
        if len(validated) != len(set(validated)):
            raise ValueError("outbox_stores must be unique")
        return validated

    @field_validator("sentinel_master")
    @classmethod
    def validate_sentinel_master(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("sentinel_master must not be empty")
        return value

    @model_validator(mode="after")
    def validate_service_kind(self) -> ServiceSpec:
        if self.kind == "redis_session":
            if not self.namespace:
                raise ValueError("redis_session namespace must not be empty")
            if self.ttl_seconds <= 0:
                raise ValueError("redis_session ttl_seconds must be positive")
            if self.queue_type != "classic":
                raise ValueError("redis_session cannot set a RabbitMQ queue_type")
        elif not self.outbox_stores:
            raise ValueError("rabbitmq outbox_stores must not be empty")
        return self


class DatabaseShardSpec(StrictSpecModel):
    shard_id: str = Field(min_length=1)
    url_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")


class DatabaseStoreSpec(StrictSpecModel):
    name: str
    global_url_env: str | None = Field(
        default=None,
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )
    shards: list[DatabaseShardSpec] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)

    @model_validator(mode="after")
    def validate_connections(self) -> DatabaseStoreSpec:
        if self.global_url_env is None and not self.shards:
            raise ValueError("Database store requires a global URL or shard URLs.")
        shard_ids = [shard.shard_id for shard in self.shards]
        if len(shard_ids) != len(set(shard_ids)):
            raise ValueError("Database shard IDs must be unique within a store.")
        return self


class DurableJobSpec(StrictSpecModel):
    """A durable, idempotent application job routed through the outbox."""

    name: str
    store: str
    event_type: str
    routing_key: str
    schedule: str | None = None

    @field_validator("name", "store")
    @classmethod
    def validate_python_names(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("event_type", "routing_key")
    @classmethod
    def validate_message_names(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Durable job message names must not be empty")
        return value

    @field_validator("schedule")
    @classmethod
    def validate_schedule(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Durable job schedule must not be empty")
        return value


class ControlPlaneHeartbeatSpec(StrictSpecModel):
    """Opt in to generated application heartbeats for an AutoForge Control Plane."""

    enabled: bool = False
    endpoint_env: str = Field(
        default="CONTROL_PLANE_HEARTBEAT_URL",
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )
    token_env: str = Field(
        default="CONTROL_PLANE_API_TOKEN",
        pattern=r"^[A-Z][A-Z0-9_]*$",
    )
    interval_seconds: int = Field(default=30, ge=5, le=3600)

    @model_validator(mode="after")
    def validate_environment_names(self) -> ControlPlaneHeartbeatSpec:
        if self.endpoint_env == self.token_env:
            raise ValueError("heartbeat endpoint_env and token_env must differ")
        return self


class ServiceTokenSpec(StrictSpecModel):
    """A named service-to-service credential accepted by generated routes."""

    name: str
    token_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)


class RuntimeEnvironmentTarget(StrEnum):
    APPLICATION = "application"
    DURABLE_JOB_WORKER = "durable_job_worker"


class RuntimeEnvironmentSpec(StrictSpecModel):
    """A user-owned runtime environment variable and its consumers."""

    name: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    required: bool = True
    health_test_value: str = Field(default="test-value", min_length=1)
    targets: list[RuntimeEnvironmentTarget] = Field(
        default_factory=lambda: [RuntimeEnvironmentTarget.APPLICATION], min_length=1
    )

    @field_validator("targets")
    @classmethod
    def validate_targets(
        cls, values: list[RuntimeEnvironmentTarget]
    ) -> list[RuntimeEnvironmentTarget]:
        if len(values) != len(set(values)):
            raise ValueError("Runtime environment targets must be unique")
        return values


class ApplicationCompositionSpec(StrictSpecModel):
    """A named, independently runnable selection of generated domain modules."""

    name: str
    modules: list[str] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, values: list[str]) -> list[str]:
        validated = [validate_python_name(value) for value in values]
        if len(validated) != len(set(validated)):
            raise ValueError("Application composition module names must be unique")
        return validated


class ApplicationSpec(StrictSpecModel):
    framework: Literal["fastapi"] = "fastapi"
    modules: list[str] = Field(default_factory=list)
    compositions: list[ApplicationCompositionSpec] = Field(default_factory=list)
    services: list[ServiceSpec] = Field(default_factory=list)
    databases: list[DatabaseStoreSpec] = Field(default_factory=list)
    durable_jobs: list[DurableJobSpec] = Field(default_factory=list)
    service_tokens: list[ServiceTokenSpec] = Field(default_factory=list)
    runtime_environments: list[RuntimeEnvironmentSpec] = Field(
        default_factory=list
    )
    control_plane_heartbeat: ControlPlaneHeartbeatSpec = Field(
        default_factory=ControlPlaneHeartbeatSpec
    )
    durable_job_worker_restart_policy: Literal[
        "no", "on-failure", "always", "unless-stopped"
    ] = "unless-stopped"

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, values: list[str]) -> list[str]:
        validated = [validate_python_name(value) for value in values]
        if len(validated) != len(set(validated)):
            raise ValueError("Application Module 이름은 중복될 수 없습니다.")
        return validated

    @model_validator(mode="after")
    def validate_services(self) -> ApplicationSpec:
        composition_names = [composition.name for composition in self.compositions]
        if len(composition_names) != len(set(composition_names)):
            raise ValueError("Application composition names must be unique")
        declared_modules = set(self.modules)
        unknown_composition_modules = sorted(
            {
                module
                for composition in self.compositions
                for module in composition.modules
                if module not in declared_modules
            }
        )
        if unknown_composition_modules:
            raise ValueError(
                "Application composition modules are not declared application "
                f"modules: {unknown_composition_modules}"
            )
        names = [service.name for service in self.services]
        if len(names) != len(set(names)):
            raise ValueError("Application Service 이름은 중복될 수 없습니다.")
        database_names = [database.name for database in self.databases]
        if len(database_names) != len(set(database_names)):
            raise ValueError("Application Database 이름은 중복될 수 없습니다.")
        job_names = [job.name for job in self.durable_jobs]
        if len(job_names) != len(set(job_names)):
            raise ValueError("Application Durable Job names must be unique")
        token_names = [token.name for token in self.service_tokens]
        if len(token_names) != len(set(token_names)):
            raise ValueError("Application service token names must be unique")
        token_environments = [token.token_env for token in self.service_tokens]
        if len(token_environments) != len(set(token_environments)):
            raise ValueError("Application service token environments must be unique")
        runtime_environment_names = [
            environment.name for environment in self.runtime_environments
        ]
        if len(runtime_environment_names) != len(set(runtime_environment_names)):
            raise ValueError("Application runtime environment names must be unique")
        reserved_environment_names = set(self.service_token_environments.values())
        if self.control_plane_heartbeat.enabled:
            reserved_environment_names.update(
                {
                    self.control_plane_heartbeat.endpoint_env,
                    self.control_plane_heartbeat.token_env,
                }
            )
        duplicate_environment_names = sorted(
            set(runtime_environment_names) & reserved_environment_names
        )
        if duplicate_environment_names:
            raise ValueError(
                "Application runtime environments conflict with generated "
                f"environments: {duplicate_environment_names}"
            )
        if (
            any(
                RuntimeEnvironmentTarget.DURABLE_JOB_WORKER in environment.targets
                for environment in self.runtime_environments
            )
            and not self.durable_jobs
        ):
            raise ValueError(
                "durable_job_worker runtime environments require durable jobs"
            )
        unknown_outbox_stores = sorted(
            {
                store
                for service in self.services
                if service.kind == "rabbitmq"
                for store in service.outbox_stores
                if store not in database_names
            }
        )
        if unknown_outbox_stores:
            raise ValueError(
                f"RabbitMQ outbox stores are not declared databases: "
                f"{unknown_outbox_stores}"
            )
        durable_job_stores = {job.store for job in self.durable_jobs}
        unknown_job_stores = sorted(durable_job_stores - set(database_names))
        if unknown_job_stores:
            raise ValueError(
                "Durable job stores are not declared databases: "
                f"{unknown_job_stores}"
            )
        databases_by_name = {database.name: database for database in self.databases}
        sharded_job_stores = sorted(
            store
            for store in durable_job_stores
            if databases_by_name[store].global_url_env is None
        )
        if sharded_job_stores:
            raise ValueError(
                "Durable job stores require a global database URL: "
                f"{sharded_job_stores}"
            )
        rabbitmq_outbox_stores = {
            store
            for service in self.services
            if service.kind == "rabbitmq"
            for store in service.outbox_stores
        }
        missing_outbox_stores = sorted(durable_job_stores - rabbitmq_outbox_stores)
        if missing_outbox_stores:
            raise ValueError(
                "Durable job stores require a RabbitMQ outbox: "
                f"{missing_outbox_stores}"
            )
        return self

    @property
    def service_token_environments(self) -> dict[str, str]:
        """Return generated service-token names and their secret environments."""

        environments = {
            token.name: token.token_env for token in self.service_tokens
        }
        if self.durable_jobs:
            environments.setdefault("durable_jobs", "DURABLE_JOB_API_TOKEN")
        return environments

    @property
    def runtime_environment_names(self) -> tuple[str, ...]:
        return tuple(environment.name for environment in self.runtime_environments)


class ToolingSpec(StrictSpecModel):
    ruff_exclude: list[str] = Field(default_factory=list)
    ci: CiSpec = Field(default_factory=lambda: CiSpec())
    docker: DockerSpec = Field(default_factory=lambda: DockerSpec())
    elk: ElkSpec = Field(default_factory=lambda: ElkSpec())
    rag: RagSpec = Field(default_factory=lambda: RagSpec())
    distributed_lock: DistributedLockSpec = Field(
        default_factory=lambda: DistributedLockSpec()
    )
    key_value_store: KeyValueStoreSpec = Field(
        default_factory=lambda: KeyValueStoreSpec()
    )
    external_provider: ExternalProviderSpec = Field(
        default_factory=lambda: ExternalProviderSpec()
    )
    email: EmailSpec = Field(default_factory=lambda: EmailSpec())
    llm: LlmSpec = Field(default_factory=lambda: LlmSpec())
    sms: SmsSpec = Field(default_factory=lambda: SmsSpec())
    notification: NotificationSpec = Field(
        default_factory=lambda: NotificationSpec()
    )
    realtime: RealtimeSpec = Field(default_factory=lambda: RealtimeSpec())
    search: SearchSpec = Field(default_factory=lambda: SearchSpec())
    storage: StorageSpec = Field(default_factory=lambda: StorageSpec())
    vector_store: VectorStoreSpec = Field(default_factory=lambda: VectorStoreSpec())
    kubernetes: KubernetesSpec = Field(default_factory=lambda: KubernetesSpec())
    single_host: SingleHostSpec = Field(default_factory=lambda: SingleHostSpec())
    local_environment: LocalEnvironmentSpec = Field(
        default_factory=lambda: LocalEnvironmentSpec()
    )

    @field_validator("ruff_exclude")
    @classmethod
    def validate_ruff_exclude(cls, values: list[str]) -> list[str]:
        normalized = [
            validate_workspace_relative_path(value).as_posix() for value in values
        ]
        if len(normalized) != len(set(normalized)):
            raise ValueError("tooling.ruff_exclude paths must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_kubernetes_collector(self) -> ToolingSpec:
        if not self.elk.kubernetes_collector_enabled:
            return self
        if not self.elk.enabled:
            raise ValueError("Kubernetes log collector requires tooling.elk.enabled")
        if not self.kubernetes.enabled:
            raise ValueError("Kubernetes log collector requires tooling.kubernetes.enabled")
        if not self.kubernetes.log_host_path:
            raise ValueError("Kubernetes log collector requires log_host_path")
        return self

    @model_validator(mode="after")
    def validate_single_host_profile(self) -> ToolingSpec:
        if not self.single_host.enabled:
            return self
        if not self.local_environment.enabled:
            raise ValueError(
                "single-host profile requires tooling.local_environment.enabled"
            )
        if not self.local_environment.application_enabled:
            raise ValueError(
                "single-host profile requires local_environment.application_enabled"
            )
        return self


class DockerSpec(StrictSpecModel):
    enabled: bool = False


class ElkSpec(StrictSpecModel):
    """Generate an optional development ELK log collection profile."""

    enabled: bool = False
    version: str = "8.19.17"
    mode: Literal["central", "collector"] = "central"
    elasticsearch_mode: Literal["standalone", "cluster"] = "standalone"
    kubernetes_collector_enabled: bool = False
    host_port_base: int = Field(default=49600, ge=49152, le=65400, multiple_of=100)

    _validate_version = field_validator("version")(validate_semantic_version)


class RagSpec(StrictSpecModel):
    """Generate an optional local RAG infrastructure overlay."""

    enabled: bool = False
    qdrant_mode: Literal["standalone", "cluster"] = "standalone"
    ollama_mode: Literal["standalone", "replicated"] = "standalone"
    search_backend: Literal["elasticsearch", "opensearch"] = "elasticsearch"
    search_mode: Literal["standalone", "cluster"] = "standalone"
    qdrant_version: str = "1.18.3"
    elasticsearch_version: str = "8.19.17"
    opensearch_version: str = "2.19.6"
    ollama_version: str = "0.32.5"
    host_port_base: int = Field(default=49400, ge=49152, le=65400, multiple_of=100)

    _validate_qdrant_version = field_validator("qdrant_version")(validate_semantic_version)
    _validate_elasticsearch_version = field_validator("elasticsearch_version")(
        validate_semantic_version
    )
    _validate_opensearch_version = field_validator("opensearch_version")(
        validate_semantic_version
    )
    _validate_ollama_version = field_validator("ollama_version")(validate_semantic_version)


class SearchSpec(StrictSpecModel):
    """Generate an opt-in application search-service boundary."""

    enabled: bool = False
    backend: Literal["elasticsearch", "opensearch"] = "elasticsearch"
    url_environment: str = Field(default="SEARCH_URL", pattern=r"^[A-Z][A-Z0-9_]*$")
    default_index: str = Field(
        default="documents", pattern=r"^[a-z0-9][a-z0-9_-]*$"
    )
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)


class ExternalProviderSpec(StrictSpecModel):
    """Generate an opt-in async external HTTP provider boundary."""

    enabled: bool = False
    url_environment: str = Field(
        default="EXTERNAL_PROVIDER_URL", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    health_path: str = Field(default="/", pattern=r"^/")
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    max_retries: int = Field(default=2, ge=0, le=5)
    retry_delay_seconds: float = Field(default=0.1, ge=0, le=5)


class RealtimeSpec(StrictSpecModel):
    """Generate an opt-in local realtime hub and optional Redis backplane."""

    enabled: bool = False
    backplane: Literal["none", "redis_pubsub"] = "none"
    channel: str = Field(
        default="realtime.notifications.v1",
        pattern=r"^[a-z][a-z0-9._-]*$",
    )
    reconnect_delay_seconds: float = Field(default=1.0, ge=0.1, le=60)

    @model_validator(mode="after")
    def validate_backplane(self) -> RealtimeSpec:
        if self.backplane != "none" and not self.enabled:
            raise ValueError("Realtime backplane requires realtime.enabled")
        return self


class NotificationSpec(StrictSpecModel):
    """Generate an opt-in outbound webhook notification boundary."""

    enabled: bool = False
    webhook_url_environment: str = Field(
        default="NOTIFICATION_WEBHOOK_URL", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)


class EmailSpec(StrictSpecModel):
    """Generate an opt-in SMTP email delivery boundary."""

    enabled: bool = False
    host_environment: str = Field(default="SMTP_HOST", pattern=r"^[A-Z][A-Z0-9_]*$")
    port_environment: str = Field(default="SMTP_PORT", pattern=r"^[A-Z][A-Z0-9_]*$")
    sender_environment: str = Field(
        default="SMTP_SENDER", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    username_environment: str = Field(
        default="SMTP_USERNAME", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    password_environment: str = Field(
        default="SMTP_PASSWORD", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    use_starttls: bool = True
    timeout_seconds: float = Field(default=10.0, gt=0, le=60)


class LlmSpec(StrictSpecModel):
    """Generate an opt-in OpenAI Responses API boundary."""

    enabled: bool = False
    model: str = ""
    api_key_environment: str = Field(
        default="OPENAI_API_KEY", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    timeout_seconds: float = Field(default=30.0, gt=0, le=120)

    @model_validator(mode="after")
    def validate_enabled_model(self) -> LlmSpec:
        if self.enabled and not self.model:
            raise ValueError("tooling.llm.model must be set when LLM is enabled")
        return self


class SmsSpec(StrictSpecModel):
    """Generate an opt-in SOLAPI SMS delivery boundary."""

    enabled: bool = False
    api_key_environment: str = Field(
        default="SOLAPI_API_KEY", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    api_secret_environment: str = Field(
        default="SOLAPI_API_SECRET", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    sender_environment: str = Field(
        default="SOLAPI_SENDER", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    timeout_seconds: float = Field(default=15.0, gt=0, le=120)


class DistributedLockSpec(StrictSpecModel):
    """Generate an opt-in Redis distributed-lock boundary."""

    enabled: bool = False
    mode: Literal["standalone", "sentinel", "cluster"] = "standalone"
    url_environment: str = Field(default="REDIS_URL", pattern=r"^[A-Z][A-Z0-9_]*$")
    cluster_url_environment: str = Field(
        default="REDIS_CLUSTER_URL", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    cluster_startup_nodes_environment: str = Field(
        default="REDIS_CLUSTER_STARTUP_NODES", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    sentinel_urls_environment: str = Field(
        default="REDIS_SENTINEL_URLS", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    sentinel_master: str = "lock-primary"
    key_prefix: str = Field(default="lock", pattern=r"^[a-z][a-z0-9:_-]*$")
    ttl_seconds: int = Field(default=30, gt=0, le=86400)

    @field_validator("sentinel_master")
    @classmethod
    def validate_sentinel_master(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("sentinel_master must not be empty")
        return value


class KeyValueStoreSpec(StrictSpecModel):
    """Generate an opt-in provider-neutral key-value store boundary."""

    enabled: bool = False
    backend: Literal["redis", "memcached"] = "redis"
    mode: Literal["standalone", "sentinel", "cluster"] = "standalone"
    url_environment: str = Field(default="REDIS_URL", pattern=r"^[A-Z][A-Z0-9_]*$")
    cluster_url_environment: str = Field(
        default="REDIS_CLUSTER_URL", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    cluster_startup_nodes_environment: str = Field(
        default="REDIS_CLUSTER_STARTUP_NODES", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    sentinel_urls_environment: str = Field(
        default="REDIS_SENTINEL_URLS", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    sentinel_master: str = "cache-primary"
    memcached_host_environment: str = Field(
        default="MEMCACHED_HOST", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    memcached_port_environment: str = Field(
        default="MEMCACHED_PORT", pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    key_prefix: str = Field(default="cache", pattern=r"^[a-z][a-z0-9:_-]*$")
    ttl_seconds: int = Field(default=300, gt=0, le=86400)

    @field_validator("sentinel_master")
    @classmethod
    def validate_sentinel_master(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("sentinel_master must not be empty")
        return value

    @model_validator(mode="after")
    def validate_backend_topology(self) -> KeyValueStoreSpec:
        if self.backend == "memcached" and self.mode != "standalone":
            raise ValueError("memcached key_value_store supports only standalone mode")
        return self


class VectorStoreSpec(StrictSpecModel):
    """Generate an opt-in Qdrant vector-store service boundary."""

    enabled: bool = False
    url_environment: str = Field(default="VECTOR_DB_URL", pattern=r"^[A-Z][A-Z0-9_]*$")
    api_key_environment: str | None = Field(
        default=None, pattern=r"^[A-Z][A-Z0-9_]*$"
    )
    default_collection: str = Field(
        default="vectors", pattern=r"^[a-z0-9][a-z0-9_-]*$"
    )
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)


class StorageSpec(StrictSpecModel):
    """Generate a local S3-compatible object storage overlay."""

    enabled: bool = True
    runtime_enabled: bool = False
    mode: Literal["standalone", "distributed"] = "standalone"
    host_port_base: int = Field(default=49500, ge=49152, le=65400, multiple_of=100)


class KubernetesMySQLOperatorSpec(StrictSpecModel):
    """Declare an opt-in MySQL Operator HA profile without rendering it yet."""

    enabled: bool = False
    bootstrap_secret_name: str = ""
    tls_secret_name: str = ""
    cluster_name: str = ""
    mysql_version: str = ""
    instances: int | None = Field(default=None, ge=3)
    router_instances: int | None = Field(default=None, ge=2)
    storage_class_name: str = ""
    storage_size: str = ""

    @model_validator(mode="after")
    def validate_enabled_profile(self) -> KubernetesMySQLOperatorSpec:
        if not self.enabled:
            return self
        required_values = {
            "bootstrap_secret_name": self.bootstrap_secret_name,
            "tls_secret_name": self.tls_secret_name,
            "cluster_name": self.cluster_name,
            "mysql_version": self.mysql_version,
            "instances": self.instances,
            "router_instances": self.router_instances,
            "storage_class_name": self.storage_class_name,
            "storage_size": self.storage_size,
        }
        missing = [name for name, value in required_values.items() if not value]
        if missing:
            raise ValueError(
                "Kubernetes MySQL Operator requires " + ", ".join(missing)
            )
        return self

    @field_validator("mysql_version")
    @classmethod
    def validate_mysql_version(cls, value: str) -> str:
        return validate_semantic_version(value) if value else value


class KubernetesControlPlaneSpec(StrictSpecModel):
    """Generate an opt-in Kubernetes-native Control Plane profile."""

    enabled: bool = False
    image: str = ""
    secret_name: str = ""
    replicas: int = Field(default=2, ge=1)

    @model_validator(mode="after")
    def validate_enabled_profile(self) -> KubernetesControlPlaneSpec:
        if self.enabled and not self.image:
            raise ValueError("Kubernetes Control Plane requires an image")
        if self.enabled and not self.secret_name:
            raise ValueError("Kubernetes Control Plane requires a secret_name")
        return self


class KubernetesSpec(StrictSpecModel):
    """Generate a zero-secret Kubernetes base_server deployment profile."""

    enabled: bool = False
    namespace: str = "default"
    image: str = ""
    secret_name: str = ""
    application_replicas: int = Field(default=3, ge=1)
    proxy_replicas: int = Field(default=2, ge=1)
    durable_job_worker_replicas: int = Field(default=1, ge=1)
    application_composition: str | None = None
    log_host_path: str | None = None
    additional_secret_env_names: list[str] = Field(default_factory=list)
    control_plane: KubernetesControlPlaneSpec = Field(
        default_factory=lambda: KubernetesControlPlaneSpec()
    )
    mysql_operator: KubernetesMySQLOperatorSpec = Field(
        default_factory=lambda: KubernetesMySQLOperatorSpec()
    )

    @field_validator("additional_secret_env_names")
    @classmethod
    def validate_additional_secret_env_names(cls, values: list[str]) -> list[str]:
        for value in values:
            if (
                not value
                or not value[0].isupper()
                or any(
                    not (character.isupper() or character.isdigit() or character == "_")
                    for character in value
                )
            ):
                raise ValueError("Kubernetes secret environment names must be uppercase")
        if len(values) != len(set(values)):
            raise ValueError("Kubernetes secret environment names must be unique")
        return values

    @field_validator("application_composition")
    @classmethod
    def validate_application_composition(cls, value: str | None) -> str | None:
        return validate_python_name(value) if value is not None else None

    @model_validator(mode="after")
    def validate_enabled_profile(self) -> KubernetesSpec:
        if self.enabled and not self.image:
            raise ValueError("Kubernetes base_server requires an image")
        if self.enabled and not self.secret_name:
            raise ValueError("Kubernetes base_server requires a secret_name")
        if self.control_plane.enabled and not self.enabled:
            raise ValueError(
                "Kubernetes Control Plane requires Kubernetes base_server"
            )
        if self.mysql_operator.enabled and not self.enabled:
            raise ValueError("Kubernetes MySQL Operator requires Kubernetes base_server")
        if (
            self.mysql_operator.enabled
            and self.mysql_operator.bootstrap_secret_name == self.secret_name
        ):
            raise ValueError(
                "Kubernetes MySQL Operator requires a separate bootstrap Secret"
            )
        if self.log_host_path and not self.log_host_path.startswith("/"):
            raise ValueError("Kubernetes log_host_path must be an absolute path")
        return self


class LocalApplicationCompositionSpec(StrictSpecModel):
    """Expose one named application composition in the local Compose profile."""

    name: str
    host_port_offset: int = Field(ge=1, le=9)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)


class LocalEnvironmentSpec(StrictSpecModel):
    """Generate a disposable Docker integration environment for declared services."""

    enabled: bool = False
    application_enabled: bool = False
    database_provider: Literal["postgresql", "mysql"] = "postgresql"
    postgres_mode: Literal["standalone", "ha"] = "standalone"
    mysql_mode: Literal["standalone", "ha"] = "standalone"
    rabbitmq_mode: Literal["standalone", "cluster"] = "standalone"
    airflow_scheduler_replicas: int = Field(default=1, ge=1)
    application_compositions: list[LocalApplicationCompositionSpec] = Field(
        default_factory=list
    )
    host_port_base: int | None = Field(
        default=None,
        ge=49152,
        le=65400,
        multiple_of=100,
        description="Optional 100-port local host block for generated Compose services.",
    )

    @model_validator(mode="after")
    def validate_database_provider(self) -> LocalEnvironmentSpec:
        if self.database_provider == "mysql" and self.postgres_mode != "standalone":
            raise ValueError("MySQL local environment supports postgres_mode=standalone only")
        if self.database_provider != "mysql" and self.mysql_mode != "standalone":
            raise ValueError("MySQL HA mode requires database_provider=mysql")
        names = [composition.name for composition in self.application_compositions]
        if len(names) != len(set(names)):
            raise ValueError("Local application composition names must be unique")
        port_offsets = [
            composition.host_port_offset
            for composition in self.application_compositions
        ]
        if len(port_offsets) != len(set(port_offsets)):
            raise ValueError("Local application composition port offsets must be unique")
        return self


class SingleHostSpec(StrictSpecModel):
    """Generate a Docker Compose operating overlay for one physical host."""

    enabled: bool = False
    application_replicas: int = Field(default=3, ge=1)
    bootstrap_provider: Literal["none", "windows_task_scheduler"] = "none"


class CiProvider(StrEnum):
    GITHUB_ACTIONS = "github_actions"
    JENKINS = "jenkins"


class CiWorkflow(StrEnum):
    TEST = "test"
    BUILD = "build"


class CiSpec(StrictSpecModel):
    providers: list[CiProvider] = Field(default_factory=list)
    workflows: list[CiWorkflow] = Field(default_factory=lambda: [CiWorkflow.TEST])

    @model_validator(mode="after")
    def validate_workflows(self) -> CiSpec:
        if len(self.providers) != len(set(self.providers)):
            raise ValueError("tooling.ci.providers must be unique")
        if len(self.workflows) != len(set(self.workflows)):
            raise ValueError("tooling.ci.workflows must be unique")
        if CiWorkflow.TEST not in self.workflows:
            raise ValueError("tooling.ci.workflows must include test")
        return self


class ProjectSpec(StrictSpecModel):
    spec_version: Literal["1"]
    project: ProjectInfo
    application: ApplicationSpec
    tooling: ToolingSpec = Field(default_factory=ToolingSpec)

    @model_validator(mode="after")
    def validate_host_port_collisions(self) -> ProjectSpec:
        realtime = self.tooling.realtime
        if realtime.backplane == "redis_pubsub":
            redis_services = [
                service
                for service in self.application.services
                if service.kind == "redis_session"
            ]
            if len(redis_services) != 1:
                raise ValueError(
                    "Redis realtime backplane requires exactly one redis_session service"
                )
        heartbeat = self.application.control_plane_heartbeat
        if heartbeat.enabled and len(self.project.package_name) > 128:
            raise ValueError(
                "Control Plane heartbeat requires a package_name of at most 128 characters"
            )
        if heartbeat.enabled and len(self.project.version) > 128:
            raise ValueError(
                "Control Plane heartbeat requires a version of at most 128 characters"
            )
        published: dict[int, list[str]] = {}

        def reserve(label: str, base: int | None, offsets: tuple[int, ...]) -> None:
            if base is None:
                return
            for offset in offsets:
                published.setdefault(base + offset, []).append(label)

        local = self.tooling.local_environment
        local_composition_names = {
            composition.name for composition in local.application_compositions
        }
        declared_composition_names = {
            composition.name for composition in self.application.compositions
        }
        kubernetes_composition = self.tooling.kubernetes.application_composition
        if kubernetes_composition and not self.tooling.kubernetes.enabled:
            raise ValueError(
                "Kubernetes application composition requires kubernetes.enabled"
            )
        if (
            kubernetes_composition
            and kubernetes_composition not in declared_composition_names
        ):
            raise ValueError(
                "Kubernetes application composition is not declared application "
                f"composition: {kubernetes_composition}"
            )
        if local_composition_names and (
            not local.enabled or not local.application_enabled
        ):
            raise ValueError(
                "Local application compositions require local_environment.enabled "
                "and application_enabled"
            )
        unknown_local_compositions = sorted(
            local_composition_names - declared_composition_names
        )
        if unknown_local_compositions:
            raise ValueError(
                "Local application compositions are not declared application "
                f"compositions: {unknown_local_compositions}"
            )
        rabbitmq_services = [
            service
            for service in self.application.services
            if service.kind == "rabbitmq"
        ]
        if local.rabbitmq_mode == "cluster":
            if not local.enabled:
                raise ValueError("RabbitMQ cluster mode requires local_environment.enabled")
            if len(rabbitmq_services) != 1:
                raise ValueError("RabbitMQ cluster mode requires one rabbitmq service")
            if rabbitmq_services[0].queue_type != "quorum":
                raise ValueError("RabbitMQ cluster mode requires queue_type=quorum")
        if (
            local.enabled
            and local.rabbitmq_mode == "standalone"
            and any(service.queue_type == "quorum" for service in rabbitmq_services)
        ):
            raise ValueError(
                "local standalone RabbitMQ cannot validate queue_type=quorum"
            )
        if local.database_provider == "mysql" and (
            rabbitmq_services or self.application.durable_jobs
        ):
            raise ValueError(
                "MySQL local runtime does not support PostgreSQL-specific messaging or durable jobs"
            )
        if local.airflow_scheduler_replicas > 1:
            if not local.enabled:
                raise ValueError(
                    "Airflow scheduler HA requires local_environment.enabled"
                )
            if not self.application.durable_jobs:
                raise ValueError("Airflow scheduler HA requires durable jobs")
            if local.postgres_mode != "ha":
                raise ValueError("Airflow scheduler HA requires postgres_mode=ha")
        if local.enabled:
            if local.application_enabled:
                reserve("local application", local.host_port_base, (0,))
            for composition in local.application_compositions:
                reserve(
                    f"local application composition {composition.name}",
                    local.host_port_base,
                    (composition.host_port_offset,),
                )
            if self.application.databases:
                reserve(f"local {local.database_provider}", local.host_port_base, (10,))
            if rabbitmq_services:
                reserve("local RabbitMQ", local.host_port_base, (30, 31))
            if self.application.durable_jobs:
                reserve("local Airflow", local.host_port_base, (40,))

        rag = self.tooling.rag
        if rag.enabled:
            reserve("RAG Qdrant", rag.host_port_base, (50, 51))
            reserve("RAG search", rag.host_port_base, (60,))
            reserve("RAG Ollama", rag.host_port_base, (70,))

        storage = self.tooling.storage
        if storage.enabled:
            reserve("object storage", storage.host_port_base, (80, 81))

        elk = self.tooling.elk
        if elk.enabled and elk.mode == "central":
            reserve("central ELK", elk.host_port_base, (0, 1))

        collisions = [
            f"{port}: {', '.join(labels)}"
            for port, labels in sorted(published.items())
            if len(labels) > 1
        ]
        if collisions:
            raise ValueError("tooling host port collision(s): " + "; ".join(collisions))
        return self


class ModuleInfo(StrictSpecModel):
    name: str
    display_name: str = Field(min_length=1, max_length=100)
    route_prefix: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("route_prefix")
    @classmethod
    def validate_route_prefix(cls, value: str) -> str:
        return validate_http_path(value)


class FieldSpec(StrictSpecModel):
    name: str
    type: FieldType
    default: object | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)


class ModelSpec(StrictSpecModel):
    name: str
    fields: list[FieldSpec] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_class_name(value)

    @model_validator(mode="after")
    def validate_unique_fields(self) -> ModelSpec:
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError(f"Model '{self.name}'의 Field 이름은 중복될 수 없습니다.")
        return self


class ColumnSpec(StrictSpecModel):
    name: str
    type: FieldType
    primary_key: bool = False
    nullable: bool = False
    default: object | None = None
    unique: bool = False
    index: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)

    @model_validator(mode="after")
    def validate_column(self) -> ColumnSpec:
        unsupported_kinds = {
            FieldTypeKind.LIST,
            FieldTypeKind.MODEL,
            FieldTypeKind.OPTIONAL,
        }
        if self.type.kind in unsupported_kinds:
            raise ValueError(
                "Database Column은 list, model 또는 optional Type을 "
                "직접 사용할 수 없습니다."
            )
        if self.primary_key and self.nullable:
            raise ValueError("Primary Key Column은 nullable일 수 없습니다.")
        return self


class TableSpec(StrictSpecModel):
    name: str
    columns: list[ColumnSpec] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_python_name(value)

    @model_validator(mode="after")
    def validate_columns(self) -> TableSpec:
        names = [column.name for column in self.columns]
        if len(names) != len(set(names)):
            raise ValueError(f"Table '{self.name}'의 Column 이름은 중복될 수 없습니다.")
        if not any(column.primary_key for column in self.columns):
            raise ValueError(f"Table '{self.name}'에는 Primary Key가 필요합니다.")
        return self


class AddColumnMigrationSpec(StrictSpecModel):
    """One additive column change for a declared existing table."""

    table: str
    column: ColumnSpec

    @field_validator("table")
    @classmethod
    def validate_table_name(cls, value: str) -> str:
        return validate_python_name(value)

    @model_validator(mode="after")
    def validate_safe_addition(self) -> AddColumnMigrationSpec:
        if self.column.primary_key:
            raise ValueError("Additive migration columns cannot be primary keys")
        if not self.column.nullable and self.column.default is None:
            raise ValueError(
                "Additive migration columns require nullable=true or a default"
            )
        return self


class DatabaseMigrationSpec(StrictSpecModel):
    """One explicit immutable revision after a module's generated baseline."""

    revision: int = Field(ge=2)
    name: str
    store: str
    create_tables: list[str] = Field(default_factory=list)
    add_columns: list[AddColumnMigrationSpec] = Field(default_factory=list)

    @field_validator("name", "store")
    @classmethod
    def validate_names(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("create_tables")
    @classmethod
    def validate_create_tables(cls, values: list[str]) -> list[str]:
        validated = [validate_python_name(value) for value in values]
        if len(validated) != len(set(validated)):
            raise ValueError("Migration create-table names must be unique")
        return validated

    @model_validator(mode="after")
    def validate_operations(self) -> DatabaseMigrationSpec:
        if not self.create_tables and not self.add_columns:
            raise ValueError("Database migration requires an additive operation")
        additions = [
            (addition.table, addition.column.name) for addition in self.add_columns
        ]
        if len(additions) != len(set(additions)):
            raise ValueError("Migration add-column targets must be unique")
        return self


class RepositoryQuerySpec(StrictSpecModel):
    name: str
    column: str
    cardinality: Literal["one", "many"] = "one"
    order_by: str | None = None
    descending: bool = False
    limit: int | None = Field(default=None, ge=1, le=1000)

    @field_validator("name", "column")
    @classmethod
    def validate_names(cls, value: str) -> str:
        return validate_python_name(value)

    @model_validator(mode="after")
    def validate_cardinality(self) -> RepositoryQuerySpec:
        if self.cardinality == "one":
            if self.order_by is not None or self.descending or self.limit is not None:
                raise ValueError("Single-result repository queries cannot define ordering")
            return self
        if self.order_by is None or self.limit is None:
            raise ValueError("Many-result repository queries require ordering and a limit")
        return self


class RepositorySpec(StrictSpecModel):
    name: str
    aggregate: str
    table: str
    operations: list[str] = Field(min_length=1)
    queries: list[RepositoryQuerySpec] = Field(default_factory=list)

    @field_validator("name", "aggregate")
    @classmethod
    def validate_class_names(cls, value: str) -> str:
        return validate_class_name(value)

    @field_validator("table")
    @classmethod
    def validate_table_name(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("operations")
    @classmethod
    def validate_operations(cls, values: list[str]) -> list[str]:
        validated = [validate_python_name(value) for value in values]
        if len(validated) != len(set(validated)):
            raise ValueError("Repository Operation 이름은 중복될 수 없습니다.")
        return validated

    @model_validator(mode="after")
    def validate_queries(self) -> RepositorySpec:
        names = [query.name for query in self.queries]
        if len(names) != len(set(names)):
            raise ValueError("Repository Query 이름은 중복될 수 없습니다.")
        return self


class DataPlacementMode(StrEnum):
    GLOBAL = "global"
    SHARDED = "sharded"


class DataPlacementSpec(StrictSpecModel):
    table: str
    store: str
    mode: DataPlacementMode = DataPlacementMode.GLOBAL
    partition_key: str | None = None
    unresolved_policy: Literal["error"] = "error"

    @field_validator("table", "store")
    @classmethod
    def validate_names(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("partition_key")
    @classmethod
    def validate_partition_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_python_name(value)

    @model_validator(mode="after")
    def validate_routing(self) -> DataPlacementSpec:
        if self.mode is DataPlacementMode.SHARDED and self.partition_key is None:
            raise ValueError("Sharded Data Placement에는 partition_key가 필요합니다.")
        return self


class DatabaseSpec(StrictSpecModel):
    provider: Literal["agnostic", "postgresql", "mysql"] = "agnostic"
    tables: list[TableSpec] = Field(default_factory=list)
    migrations: list[DatabaseMigrationSpec] = Field(default_factory=list)
    repositories: list[RepositorySpec] = Field(default_factory=list)
    placements: list[DataPlacementSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_database(self) -> DatabaseSpec:
        self._validate_unique_names(
            [table.name for table in self.tables],
            "Database Table",
        )
        self._validate_unique_names(
            [repository.name for repository in self.repositories],
            "Repository",
        )
        self._validate_unique_names(
            [placement.table for placement in self.placements],
            "Data Placement Table",
        )

        tables = {table.name: table for table in self.tables}
        placements = {placement.table: placement for placement in self.placements}
        migration_keys = [
            (migration.store, migration.revision) for migration in self.migrations
        ]
        if len(migration_keys) != len(set(migration_keys)):
            raise ValueError("Database migration store and revision pairs must be unique")
        created_tables: set[str] = set()
        added_columns: set[tuple[str, str]] = set()
        for migration in self.migrations:
            placement_modes: set[DataPlacementMode] = set()
            for table_name in migration.create_tables:
                table = tables.get(table_name)
                placement = placements.get(table_name)
                if table is None or placement is None or placement.store != migration.store:
                    raise ValueError(
                        "Migration create table must be declared in its target store: "
                        f"{table_name}"
                    )
                if table_name in created_tables:
                    raise ValueError(f"Migration table is created more than once: {table_name}")
                created_tables.add(table_name)
                placement_modes.add(placement.mode)
            for addition in migration.add_columns:
                table = tables.get(addition.table)
                placement = placements.get(addition.table)
                if table is None or placement is None or placement.store != migration.store:
                    raise ValueError(
                        "Migration add column must target a declared table in its "
                        f"store: {addition.table}"
                    )
                if addition.table in migration.create_tables:
                    raise ValueError(
                        "Migration add column cannot target a table created by the "
                        "same revision"
                    )
                if addition.column.name not in {column.name for column in table.columns}:
                    raise ValueError(
                        "Migration add column is not declared on its table: "
                        f"{addition.table}.{addition.column.name}"
                    )
                target = (addition.table, addition.column.name)
                if target in added_columns:
                    raise ValueError(
                        "Migration column is added more than once: "
                        f"{addition.table}.{addition.column.name}"
                    )
                added_columns.add(target)
                placement_modes.add(placement.mode)
            if len(placement_modes) != 1:
                raise ValueError(
                    "Database migration operations must share one placement mode"
                )
        for repository in self.repositories:
            if repository.table not in tables:
                raise ValueError(
                    f"Repository '{repository.name}'이 참조하는 Table이 없습니다: "
                    f"{repository.table}"
                )
            table = tables[repository.table]
            columns = {column.name: column for column in table.columns}
            for query in repository.queries:
                column = columns.get(query.column)
                if column is None:
                    raise ValueError(
                        f"Repository '{repository.name}' Query '{query.name}'이 "
                        f"참조하는 Column이 없습니다: {query.column}"
                    )
                if query.cardinality == "many":
                    if not column.index:
                        raise ValueError(
                            f"Repository '{repository.name}' Query '{query.name}' "
                            "must use an indexed filter column"
                        )
                    assert query.order_by is not None
                    order_column = columns.get(query.order_by)
                    if order_column is None:
                        raise ValueError(
                            f"Repository '{repository.name}' Query '{query.name}' "
                            f"references unknown order column: {query.order_by}"
                        )
                    if not order_column.index:
                        raise ValueError(
                            f"Repository '{repository.name}' Query '{query.name}' "
                            "must use an indexed order column"
                        )
                elif not (column.unique or column.primary_key):
                    raise ValueError(
                        f"Repository '{repository.name}' Query '{query.name}'은 "
                        f"unique Column을 참조해야 합니다: {query.column}"
                    )

        for placement in self.placements:
            table = tables.get(placement.table)
            if table is None:
                raise ValueError(
                    f"Data Placement가 참조하는 Table이 없습니다: {placement.table}"
                )
            column_names = {column.name for column in table.columns}
            if (
                placement.partition_key is not None
                and placement.partition_key not in column_names
            ):
                raise ValueError(
                    f"Table '{placement.table}'에 partition_key Column이 없습니다: "
                    f"{placement.partition_key}"
                )
        return self

    @staticmethod
    def _validate_unique_names(names: list[str], label: str) -> None:
        if len(names) != len(set(names)):
            raise ValueError(f"{label} 이름은 중복될 수 없습니다.")


class SchemaSpec(StrictSpecModel):
    fields: list[FieldSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_fields(self) -> SchemaSpec:
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("Schema Field 이름은 중복될 수 없습니다.")
        return self


class ResponseSpec(SchemaSpec):
    model_name: str | None = Field(default=None, alias="model")

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_class_name(value)

    @model_validator(mode="after")
    def validate_response_shape(self) -> ResponseSpec:
        if self.model_name is not None and self.fields:
            raise ValueError("Response에는 model과 fields를 동시에 지정할 수 없습니다.")
        return self


class EndpointSpec(StrictSpecModel):
    name: str
    method: HttpMethod
    path: str
    request: SchemaSpec | None = None
    response: ResponseSpec
    handler: str
    dependencies: list[EndpointDependency] = Field(default_factory=list)
    service_token: str | None = None
    access_level: EndpointAccessLevel | None = None
    idempotency: bool = False
    idempotency_ttl_seconds: int = Field(default=86400, ge=1, le=604800)

    @field_validator("name", "handler")
    @classmethod
    def validate_python_names(cls, value: str) -> str:
        return validate_python_name(value)

    @field_validator("service_token")
    @classmethod
    def validate_service_token(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_python_name(value)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return validate_http_path(value)

    @field_validator("dependencies")
    @classmethod
    def validate_unique_dependencies(
        cls,
        values: list[EndpointDependency],
    ) -> list[EndpointDependency]:
        if len(values) != len(set(values)):
            raise ValueError("Endpoint dependencies must be unique.")
        return values

    @model_validator(mode="after")
    def validate_access_boundary(self) -> EndpointSpec:
        if self.idempotency and self.method is HttpMethod.GET:
            raise ValueError("GET endpoints cannot enable idempotency")
        if self.access_level is None:
            return self
        if self.service_token is not None:
            raise ValueError(
                "Endpoint access_level and service_token cannot be combined."
            )
        if EndpointDependency.CURRENT_SESSION not in self.dependencies:
            raise ValueError(
                "Endpoint access_level requires the current_session dependency."
            )
        return self


class ModuleSpec(StrictSpecModel):
    spec_version: Literal["1"]
    module: ModuleInfo
    models: list[ModelSpec] = Field(default_factory=list)
    endpoints: list[EndpointSpec] = Field(default_factory=list)
    database: DatabaseSpec | None = None

    @model_validator(mode="after")
    def validate_module(self) -> ModuleSpec:
        model_names = [model.name for model in self.models]
        if len(model_names) != len(set(model_names)):
            raise ValueError("Module Model 이름은 중복될 수 없습니다.")

        endpoint_names = [endpoint.name for endpoint in self.endpoints]
        if len(endpoint_names) != len(set(endpoint_names)):
            raise ValueError("Module Endpoint 이름은 중복될 수 없습니다.")

        known_models = set(model_names)
        if self.database is not None:
            for repository in self.database.repositories:
                if repository.aggregate not in known_models:
                    raise ValueError(
                        f"Repository '{repository.name}'이 참조하는 Aggregate "
                        f"Model이 없습니다: {repository.aggregate}"
                    )
        for model in self.models:
            for field in model.fields:
                self._validate_type_references(field.type, known_models)

        for endpoint in self.endpoints:
            if endpoint.request is not None:
                for field in endpoint.request.fields:
                    self._validate_type_references(field.type, known_models)
            for field in endpoint.response.fields:
                self._validate_type_references(field.type, known_models)
            if (
                endpoint.response.model_name is not None
                and endpoint.response.model_name not in known_models
            ):
                raise ValueError(
                    f"정의되지 않은 Response Model입니다: "
                    f"{endpoint.response.model_name}"
                )
        return self

    @classmethod
    def _validate_type_references(
        cls,
        field_type: FieldType,
        known_models: set[str],
    ) -> None:
        if (
            field_type.kind is FieldTypeKind.MODEL
            and field_type.reference not in known_models
        ):
            raise ValueError(f"정의되지 않은 Model 참조입니다: {field_type.reference}")
        if field_type.item is not None:
            cls._validate_type_references(field_type.item, known_models)
