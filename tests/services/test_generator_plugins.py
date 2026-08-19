from pathlib import PurePosixPath

from autoforge.core.specification import (
    ApplicationSpec,
    CiProvider,
    CiSpec,
    DatabaseStoreSpec,
    DockerSpec,
    ExternalProviderSpec,
    KubernetesSpec,
    LocalEnvironmentSpec,
    ModuleInfo,
    ModuleSpec,
    ProjectInfo,
    ProjectSpec,
    RagSpec,
    SearchSpec,
    StorageSpec,
    ToolingSpec,
    VectorStoreSpec,
)
from autoforge.services.generation import create_fastapi_generator_plugins
from autoforge.services.generation.alembic import (
    ALEMBIC_BASELINE_GENERATOR_ID,
    ALEMBIC_PROJECT_GENERATOR_ID,
)
from autoforge.services.generation.ci import CI_GENERATOR_ID
from autoforge.services.generation.dockerfile import DOCKERFILE_GENERATOR_ID
from autoforge.services.generation.durable_jobs import DURABLE_JOB_GENERATOR_ID
from autoforge.services.generation.elk import ELK_GENERATOR_ID
from autoforge.services.generation.external_provider import (
    EXTERNAL_PROVIDER_GENERATOR_ID,
)
from autoforge.services.generation.fastapi_module import MODULE_GENERATOR_ID
from autoforge.services.generation.fastapi_project import GENERATOR_ID
from autoforge.services.generation.kubernetes import (
    KUBERNETES_BASE_SERVER_GENERATOR_ID,
)
from autoforge.services.generation.local_environment import (
    LOCAL_ENVIRONMENT_GENERATOR_ID,
)
from autoforge.services.generation.messaging import MESSAGING_GENERATOR_ID
from autoforge.services.generation.mysql_ddl import MYSQL_DDL_GENERATOR_ID
from autoforge.services.generation.postgresql_ddl import (
    POSTGRESQL_DDL_GENERATOR_ID,
)
from autoforge.services.generation.rag import RAG_INFRASTRUCTURE_GENERATOR_ID
from autoforge.services.generation.repository import REPOSITORY_GENERATOR_ID
from autoforge.services.generation.search import SEARCH_SERVICE_GENERATOR_ID
from autoforge.services.generation.session_store import SESSION_STORE_GENERATOR_ID
from autoforge.services.generation.single_host import SINGLE_HOST_GENERATOR_ID
from autoforge.services.generation.sqlalchemy import (
    SQLALCHEMY_MODEL_GENERATOR_ID,
    SQLALCHEMY_PROJECT_GENERATOR_ID,
)
from autoforge.services.generation.storage import OBJECT_STORAGE_GENERATOR_ID
from autoforge.services.generation.vector_store import VECTOR_STORE_GENERATOR_ID


def test_fastapi_generator_plugins_register_real_generators() -> None:
    plugins = create_fastapi_generator_plugins("game_server")

    assert plugins.project.names() == [
        ALEMBIC_PROJECT_GENERATOR_ID,
        CI_GENERATOR_ID,
        DOCKERFILE_GENERATOR_ID,
        ELK_GENERATOR_ID,
        GENERATOR_ID,
        KUBERNETES_BASE_SERVER_GENERATOR_ID,
        LOCAL_ENVIRONMENT_GENERATOR_ID,
        RAG_INFRASTRUCTURE_GENERATOR_ID,
        DURABLE_JOB_GENERATOR_ID,
        EXTERNAL_PROVIDER_GENERATOR_ID,
        MESSAGING_GENERATOR_ID,
        SEARCH_SERVICE_GENERATOR_ID,
        SESSION_STORE_GENERATOR_ID,
        VECTOR_STORE_GENERATOR_ID,
        SINGLE_HOST_GENERATOR_ID,
        SQLALCHEMY_PROJECT_GENERATOR_ID,
        OBJECT_STORAGE_GENERATOR_ID,
    ]
    assert plugins.module.names() == [
        ALEMBIC_BASELINE_GENERATOR_ID,
        MODULE_GENERATOR_ID,
        MYSQL_DDL_GENERATOR_ID,
        POSTGRESQL_DDL_GENERATOR_ID,
        REPOSITORY_GENERATOR_ID,
        SQLALCHEMY_MODEL_GENERATOR_ID,
    ]


def test_project_generator_plugin_preserves_project_spec_type() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
    )

    rendered = plugins.project.get(GENERATOR_ID).render(specification)

    assert PurePosixPath("src/game_server/main.py") in rendered


def test_dockerfile_generator_plugin_is_empty_until_enabled() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
    )

    assert plugins.project.get(DOCKERFILE_GENERATOR_ID).render(specification) == {}

    requested = specification.model_copy(
        update={"tooling": ToolingSpec(docker=DockerSpec(enabled=True))}
    )
    rendered = plugins.project.get(DOCKERFILE_GENERATOR_ID).render(requested)

    assert PurePosixPath("Dockerfile") in rendered


def test_local_environment_generator_plugin_is_empty_until_enabled() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(
            databases=[DatabaseStoreSpec(name="identity", global_url_env="DATABASE_URL")]
        ),
    )

    assert plugins.project.get(LOCAL_ENVIRONMENT_GENERATOR_ID).render(specification) == {}

    requested = specification.model_copy(
        update={
            "tooling": ToolingSpec(
                local_environment=LocalEnvironmentSpec(enabled=True)
            )
        }
    )
    rendered = plugins.project.get(LOCAL_ENVIRONMENT_GENERATOR_ID).render(requested)

    assert PurePosixPath("environment", "compose.integration.yml") in rendered


def test_rag_infrastructure_generator_plugin_is_empty_until_enabled() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
    )

    assert plugins.project.get(RAG_INFRASTRUCTURE_GENERATOR_ID).render(specification) == {}

    requested = specification.model_copy(
        update={"tooling": ToolingSpec(rag=RagSpec(enabled=True))}
    )
    rendered = plugins.project.get(RAG_INFRASTRUCTURE_GENERATOR_ID).render(requested)

    assert PurePosixPath("deploy", "rag", "compose.rag.yaml") in rendered


def test_search_service_generator_plugin_is_empty_until_enabled() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
    )

    assert plugins.project.get(SEARCH_SERVICE_GENERATOR_ID).render(specification) == {}

    requested = specification.model_copy(
        update={"tooling": ToolingSpec(search=SearchSpec(enabled=True))}
    )
    rendered = plugins.project.get(SEARCH_SERVICE_GENERATOR_ID).render(requested)

    assert PurePosixPath(
        "src", "game_server", "infrastructure", "search", "service.py"
    ) in rendered


def test_external_provider_generator_plugin_is_empty_until_enabled() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
    )

    assert plugins.project.get(EXTERNAL_PROVIDER_GENERATOR_ID).render(specification) == {}

    requested = specification.model_copy(
        update={
            "tooling": ToolingSpec(
                external_provider=ExternalProviderSpec(enabled=True)
            )
        }
    )
    rendered = plugins.project.get(EXTERNAL_PROVIDER_GENERATOR_ID).render(requested)

    assert PurePosixPath(
        "src", "game_server", "infrastructure", "external_provider", "service.py"
    ) in rendered


def test_vector_store_generator_plugin_is_empty_until_enabled() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
    )

    assert plugins.project.get(VECTOR_STORE_GENERATOR_ID).render(specification) == {}

    requested = specification.model_copy(
        update={"tooling": ToolingSpec(vector_store=VectorStoreSpec(enabled=True))}
    )
    rendered = plugins.project.get(VECTOR_STORE_GENERATOR_ID).render(requested)

    assert PurePosixPath(
        "src", "game_server", "infrastructure", "vector_store", "service.py"
    ) in rendered


def test_object_storage_generator_plugin_renders_by_default_and_can_be_disabled() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
    )

    rendered = plugins.project.get(OBJECT_STORAGE_GENERATOR_ID).render(specification)

    assert PurePosixPath("deploy", "storage", "compose.storage.yaml") in rendered

    disabled = specification.model_copy(
        update={"tooling": ToolingSpec(storage=StorageSpec(enabled=False))}
    )

    assert plugins.project.get(OBJECT_STORAGE_GENERATOR_ID).render(disabled) == {}


def test_kubernetes_base_server_plugin_is_empty_until_enabled() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
    )

    assert (
        plugins.project.get(KUBERNETES_BASE_SERVER_GENERATOR_ID).render(
            specification
        )
        == {}
    )

    requested = specification.model_copy(
        update={
            "tooling": ToolingSpec(
                kubernetes=KubernetesSpec(
                    enabled=True,
                    image="game-server:latest",
                    secret_name="game-server-runtime",
                )
            )
        }
    )
    rendered = plugins.project.get(KUBERNETES_BASE_SERVER_GENERATOR_ID).render(
        requested
    )

    assert PurePosixPath("deploy", "kubernetes", "base-server.yaml") in rendered


def test_ci_generator_plugin_is_empty_until_ci_is_requested() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server", package_name="game_server", version="0.1.0"
        ),
        application=ApplicationSpec(),
    )

    assert plugins.project.get(CI_GENERATOR_ID).render(specification) == {}

    requested = specification.model_copy(
        update={
            "tooling": specification.tooling.model_copy(
                update={"ci": CiSpec(providers=[CiProvider.GITHUB_ACTIONS])}
            )
        }
    )
    rendered = plugins.project.get(CI_GENERATOR_ID).render(requested)

    assert PurePosixPath(".github/workflows/ci.yml") in rendered


def test_module_generator_plugin_preserves_module_spec_type() -> None:
    plugins = create_fastapi_generator_plugins("game_server")
    specification = ModuleSpec(
        spec_version="1",
        module=ModuleInfo(
            name="tutorial",
            display_name="Tutorial",
            route_prefix="/api/tutorial",
        ),
    )

    rendered = plugins.module.get(MODULE_GENERATOR_ID).render(specification)

    assert (
        PurePosixPath("src/game_server/modules/tutorial/generated/router.py")
        in rendered
    )
