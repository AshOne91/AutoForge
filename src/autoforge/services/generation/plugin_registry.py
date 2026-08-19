from dataclasses import dataclass

from autoforge.core.plugin import (
    GeneratorPluginAdapter,
    GeneratorPluginRegistry,
    PluginCapability,
    PluginMetadata,
)
from autoforge.core.specification import ModuleSpec, ProjectSpec
from autoforge.services.generation.alembic import (
    ALEMBIC_BASELINE_GENERATOR_ID,
    ALEMBIC_GENERATOR_VERSION,
    ALEMBIC_PROJECT_GENERATOR_ID,
    AlembicBaselineGenerator,
    AlembicEnvironmentGenerator,
)
from autoforge.services.generation.ci import (
    CI_GENERATOR_ID,
    CI_GENERATOR_VERSION,
    CIGenerator,
)
from autoforge.services.generation.dockerfile import (
    DOCKERFILE_GENERATOR_ID,
    DOCKERFILE_GENERATOR_VERSION,
    DockerfileGenerator,
)
from autoforge.services.generation.durable_jobs import (
    DURABLE_JOB_GENERATOR_ID,
    DURABLE_JOB_GENERATOR_VERSION,
    DurableJobGenerator,
)
from autoforge.services.generation.elk import (
    ELK_GENERATOR_ID,
    ELK_GENERATOR_VERSION,
    ElkStackGenerator,
)
from autoforge.services.generation.external_provider import (
    EXTERNAL_PROVIDER_GENERATOR_ID,
    EXTERNAL_PROVIDER_GENERATOR_VERSION,
    ExternalProviderGenerator,
)
from autoforge.services.generation.fastapi_module import (
    MODULE_GENERATOR_ID,
    MODULE_GENERATOR_VERSION,
    FastAPIModuleGenerator,
)
from autoforge.services.generation.fastapi_project import (
    GENERATOR_ID,
    GENERATOR_VERSION,
    FastAPIProjectGenerator,
)
from autoforge.services.generation.kubernetes import (
    KUBERNETES_BASE_SERVER_GENERATOR_ID,
    KUBERNETES_BASE_SERVER_GENERATOR_VERSION,
    KubernetesBaseServerGenerator,
)
from autoforge.services.generation.local_environment import (
    LOCAL_ENVIRONMENT_GENERATOR_ID,
    LOCAL_ENVIRONMENT_GENERATOR_VERSION,
    LocalEnvironmentGenerator,
)
from autoforge.services.generation.messaging import (
    MESSAGING_GENERATOR_ID,
    MESSAGING_GENERATOR_VERSION,
    MessagingGenerator,
)
from autoforge.services.generation.mysql_ddl import (
    MYSQL_DDL_GENERATOR_ID,
    MYSQL_DDL_GENERATOR_VERSION,
    MySQLDDLGenerator,
)
from autoforge.services.generation.postgresql_ddl import (
    POSTGRESQL_DDL_GENERATOR_ID,
    POSTGRESQL_DDL_GENERATOR_VERSION,
    PostgreSQLDDLGenerator,
)
from autoforge.services.generation.rag import (
    RAG_INFRASTRUCTURE_GENERATOR_ID,
    RAG_INFRASTRUCTURE_GENERATOR_VERSION,
    RagInfrastructureGenerator,
)
from autoforge.services.generation.repository import (
    REPOSITORY_GENERATOR_ID,
    REPOSITORY_GENERATOR_VERSION,
    RepositoryGenerator,
)
from autoforge.services.generation.search import (
    SEARCH_SERVICE_GENERATOR_ID,
    SEARCH_SERVICE_GENERATOR_VERSION,
    SearchServiceGenerator,
)
from autoforge.services.generation.session_store import (
    SESSION_STORE_GENERATOR_ID,
    SESSION_STORE_GENERATOR_VERSION,
    SessionStoreGenerator,
)
from autoforge.services.generation.single_host import (
    SINGLE_HOST_GENERATOR_ID,
    SINGLE_HOST_GENERATOR_VERSION,
    SingleHostOperatingGenerator,
)
from autoforge.services.generation.sqlalchemy import (
    SQLALCHEMY_GENERATOR_VERSION,
    SQLALCHEMY_MODEL_GENERATOR_ID,
    SQLALCHEMY_PROJECT_GENERATOR_ID,
    SQLAlchemyInfrastructureGenerator,
    SQLAlchemyModelGenerator,
)
from autoforge.services.generation.storage import (
    OBJECT_STORAGE_GENERATOR_ID,
    OBJECT_STORAGE_GENERATOR_VERSION,
    ObjectStorageGenerator,
)
from autoforge.services.generation.vector_store import (
    VECTOR_STORE_GENERATOR_ID,
    VECTOR_STORE_GENERATOR_VERSION,
    VectorStoreGenerator,
)


@dataclass(frozen=True, slots=True)
class FastAPIGeneratorPlugins:
    project: GeneratorPluginRegistry[ProjectSpec]
    module: GeneratorPluginRegistry[ModuleSpec]


def create_fastapi_generator_plugins(
    package_name: str,
) -> FastAPIGeneratorPlugins:
    project_registry = GeneratorPluginRegistry[ProjectSpec]()
    project_registry.register(
        GeneratorPluginAdapter(
            CIGenerator(),
            PluginMetadata(
                name=CI_GENERATOR_ID,
                version=CI_GENERATOR_VERSION,
                description="GitHub Actions와 Jenkins 검증 CI Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            MessagingGenerator(),
            PluginMetadata(
                name=MESSAGING_GENERATOR_ID,
                version=MESSAGING_GENERATOR_VERSION,
                description="RabbitMQ Transport와 Transactional Outbox Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            AlembicEnvironmentGenerator(),
            PluginMetadata(
                name=ALEMBIC_PROJECT_GENERATOR_ID,
                version=ALEMBIC_GENERATOR_VERSION,
                description="Store별 Alembic async 실행 환경 Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            DurableJobGenerator(),
            PluginMetadata(
                name=DURABLE_JOB_GENERATOR_ID,
                version=DURABLE_JOB_GENERATOR_VERSION,
                description="Durable Job과 Transactional Outbox 계약 Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            FastAPIProjectGenerator(),
            PluginMetadata(
                name=GENERATOR_ID,
                version=GENERATOR_VERSION,
                description="FastAPI 프로젝트 구조 Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            DockerfileGenerator(),
            PluginMetadata(
                name=DOCKERFILE_GENERATOR_ID,
                version=DOCKERFILE_GENERATOR_VERSION,
                description="Python 3.12 build-only Dockerfile Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            ElkStackGenerator(),
            PluginMetadata(
                name=ELK_GENERATOR_ID,
                version=ELK_GENERATOR_VERSION,
                description="Development Elasticsearch, Kibana and Filebeat overlay Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            ExternalProviderGenerator(),
            PluginMetadata(
                name=EXTERNAL_PROVIDER_GENERATOR_ID,
                version=EXTERNAL_PROVIDER_GENERATOR_VERSION,
                description="Async external HTTP provider Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            RagInfrastructureGenerator(),
            PluginMetadata(
                name=RAG_INFRASTRUCTURE_GENERATOR_ID,
                version=RAG_INFRASTRUCTURE_GENERATOR_VERSION,
                description="Local Qdrant, Elasticsearch and optional Ollama RAG overlay Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            SearchServiceGenerator(),
            PluginMetadata(
                name=SEARCH_SERVICE_GENERATOR_ID,
                version=SEARCH_SERVICE_GENERATOR_VERSION,
                description="Async Elasticsearch/OpenSearch SearchService Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            LocalEnvironmentGenerator(),
            PluginMetadata(
                name=LOCAL_ENVIRONMENT_GENERATOR_ID,
                version=LOCAL_ENVIRONMENT_GENERATOR_VERSION,
                description="선언된 서비스용 로컬 Docker 통합 환경 Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            SingleHostOperatingGenerator(),
            PluginMetadata(
                name=SINGLE_HOST_GENERATOR_ID,
                version=SINGLE_HOST_GENERATOR_VERSION,
                description="단일 물리 Docker host 운영 오버레이 Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            KubernetesBaseServerGenerator(),
            PluginMetadata(
                name=KUBERNETES_BASE_SERVER_GENERATOR_ID,
                version=KUBERNETES_BASE_SERVER_GENERATOR_VERSION,
                description="Zero-secret Kubernetes Proxy/App base_server Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            SQLAlchemyInfrastructureGenerator(),
            PluginMetadata(
                name=SQLALCHEMY_PROJECT_GENERATOR_ID,
                version=SQLALCHEMY_GENERATOR_VERSION,
                description="SQLAlchemy async database infrastructure Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            SessionStoreGenerator(),
            PluginMetadata(
                name=SESSION_STORE_GENERATOR_ID,
                version=SESSION_STORE_GENERATOR_VERSION,
                description="SessionStore Protocol, Fake와 Redis Adapter Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            ObjectStorageGenerator(),
            PluginMetadata(
                name=OBJECT_STORAGE_GENERATOR_ID,
                version=OBJECT_STORAGE_GENERATOR_VERSION,
                description="Local MinIO S3-compatible object storage overlay Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    project_registry.register(
        GeneratorPluginAdapter(
            VectorStoreGenerator(),
            PluginMetadata(
                name=VECTOR_STORE_GENERATOR_ID,
                version=VECTOR_STORE_GENERATOR_VERSION,
                description="Async Qdrant VectorStore Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )

    module_registry = GeneratorPluginRegistry[ModuleSpec]()
    module_registry.register(
        GeneratorPluginAdapter(
            AlembicBaselineGenerator(),
            PluginMetadata(
                name=ALEMBIC_BASELINE_GENERATOR_ID,
                version=ALEMBIC_GENERATOR_VERSION,
                description="불변 Alembic baseline revision Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    module_registry.register(
        GeneratorPluginAdapter(
            FastAPIModuleGenerator(package_name),
            PluginMetadata(
                name=MODULE_GENERATOR_ID,
                version=MODULE_GENERATOR_VERSION,
                description="FastAPI 도메인 Module Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    module_registry.register(
        GeneratorPluginAdapter(
            RepositoryGenerator(package_name),
            PluginMetadata(
                name=REPOSITORY_GENERATOR_ID,
                version=REPOSITORY_GENERATOR_VERSION,
                description="기술 중립 Repository Protocol과 Fake Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    module_registry.register(
        GeneratorPluginAdapter(
            PostgreSQLDDLGenerator(),
            PluginMetadata(
                name=POSTGRESQL_DDL_GENERATOR_ID,
                version=POSTGRESQL_DDL_GENERATOR_VERSION,
                description="PostgreSQL global/sharded DDL Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    module_registry.register(
        GeneratorPluginAdapter(
            MySQLDDLGenerator(),
            PluginMetadata(
                name=MYSQL_DDL_GENERATOR_ID,
                version=MYSQL_DDL_GENERATOR_VERSION,
                description="MySQL global/sharded DDL Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    module_registry.register(
        GeneratorPluginAdapter(
            SQLAlchemyModelGenerator(package_name),
            PluginMetadata(
                name=SQLALCHEMY_MODEL_GENERATOR_ID,
                version=SQLALCHEMY_GENERATOR_VERSION,
                description="SQLAlchemy 2.x annotated model Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    return FastAPIGeneratorPlugins(
        project=project_registry,
        module=module_registry,
    )
