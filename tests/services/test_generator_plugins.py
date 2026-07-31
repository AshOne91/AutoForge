from pathlib import PurePosixPath

from autoforge.core.specification import (
    ApplicationSpec,
    ModuleInfo,
    ModuleSpec,
    ProjectInfo,
    ProjectSpec,
)
from autoforge.services.generation import create_fastapi_generator_plugins
from autoforge.services.generation.fastapi_module import MODULE_GENERATOR_ID
from autoforge.services.generation.fastapi_project import GENERATOR_ID
from autoforge.services.generation.postgresql_ddl import (
    POSTGRESQL_DDL_GENERATOR_ID,
)
from autoforge.services.generation.repository import REPOSITORY_GENERATOR_ID
from autoforge.services.generation.session_store import SESSION_STORE_GENERATOR_ID
from autoforge.services.generation.sqlalchemy import (
    SQLALCHEMY_MODEL_GENERATOR_ID,
    SQLALCHEMY_PROJECT_GENERATOR_ID,
)


def test_fastapi_generator_plugins_register_real_generators() -> None:
    plugins = create_fastapi_generator_plugins("game_server")

    assert plugins.project.names() == [
        GENERATOR_ID,
        SESSION_STORE_GENERATOR_ID,
        SQLALCHEMY_PROJECT_GENERATOR_ID,
    ]
    assert plugins.module.names() == [
        MODULE_GENERATOR_ID,
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
