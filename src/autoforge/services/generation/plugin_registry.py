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
from autoforge.services.generation.messaging import (
    MESSAGING_GENERATOR_ID,
    MESSAGING_GENERATOR_VERSION,
    MessagingGenerator,
)
from autoforge.services.generation.postgresql_ddl import (
    POSTGRESQL_DDL_GENERATOR_ID,
    POSTGRESQL_DDL_GENERATOR_VERSION,
    PostgreSQLDDLGenerator,
)
from autoforge.services.generation.repository import (
    REPOSITORY_GENERATOR_ID,
    REPOSITORY_GENERATOR_VERSION,
    RepositoryGenerator,
)
from autoforge.services.generation.session_store import (
    SESSION_STORE_GENERATOR_ID,
    SESSION_STORE_GENERATOR_VERSION,
    SessionStoreGenerator,
)
from autoforge.services.generation.sqlalchemy import (
    SQLALCHEMY_GENERATOR_VERSION,
    SQLALCHEMY_MODEL_GENERATOR_ID,
    SQLALCHEMY_PROJECT_GENERATOR_ID,
    SQLAlchemyInfrastructureGenerator,
    SQLAlchemyModelGenerator,
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
