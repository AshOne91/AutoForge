import ast
import tomllib
from pathlib import PurePosixPath

from autoforge.core.generation import (
    FileOwnership,
    Generator,
    content_hash,
)
from autoforge.core.specification import ApplicationSpec, ProjectInfo, ProjectSpec
from autoforge.services.generation import FastAPIProjectGenerator


def project_specification(
    *,
    name: str = "Game Server",
    description: str = "모듈형 FastAPI 게임 서버",
    modules: list[str] | None = None,
) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name=name,
            package_name="game_server",
            version="0.1.0",
            description=description,
        ),
        application=ApplicationSpec(modules=modules or []),
    )


def test_fastapi_project_generator_satisfies_protocol() -> None:
    generator: Generator[ProjectSpec] = FastAPIProjectGenerator()

    assert isinstance(generator, Generator)


def test_render_returns_minimum_fastapi_project_files() -> None:
    files = FastAPIProjectGenerator().render(project_specification())

    assert set(files) == {
        PurePosixPath("pyproject.toml"),
        PurePosixPath("README.md"),
        PurePosixPath("src/game_server/__init__.py"),
        PurePosixPath("src/game_server/main.py"),
        PurePosixPath("src/game_server/modules/__init__.py"),
        PurePosixPath("src/game_server/application/__init__.py"),
        PurePosixPath("src/game_server/application/app_factory.py"),
        PurePosixPath("src/game_server/application/generated/__init__.py"),
        PurePosixPath("src/game_server/application/generated/module_registry.py"),
        PurePosixPath("src/game_server/routers/__init__.py"),
        PurePosixPath("src/game_server/routers/health.py"),
        PurePosixPath("tests/test_health.py"),
    }


def test_render_uses_project_information() -> None:
    files = FastAPIProjectGenerator().render(
        project_specification(name="Tutorial Server")
    )

    assert (
        'title="Tutorial Server"'
        in files[PurePosixPath("src/game_server/application/app_factory.py")]
    )
    assert (
        "from game_server.application"
        in files[PurePosixPath("src/game_server/main.py")]
    )
    assert 'pip install -e ".[test]"' in files[PurePosixPath("README.md")]
    assert "uvicorn game_server.main:app" in files[PurePosixPath("README.md")]


def test_render_empty_module_registry() -> None:
    files = FastAPIProjectGenerator().render(project_specification())
    registry = files[
        PurePosixPath("src/game_server/application/generated/module_registry.py")
    ]

    assert "MODULE_ROUTERS: tuple[APIRouter, ...] = ()" in registry


def test_render_module_registry_in_declared_order() -> None:
    files = FastAPIProjectGenerator().render(
        project_specification(modules=["tutorial", "item"])
    )
    registry = files[
        PurePosixPath("src/game_server/application/generated/module_registry.py")
    ]

    tutorial_import = (
        "from game_server.modules.tutorial.generated.router "
        "import router as tutorial_router"
    )
    item_import = (
        "from game_server.modules.item.generated.router import router as item_router"
    )
    assert registry.index(tutorial_import) < registry.index(item_import)
    assert "    tutorial_router,\n    item_router,\n" in registry


def test_app_factory_registers_module_routers() -> None:
    files = FastAPIProjectGenerator().render(project_specification())
    app_factory = files[PurePosixPath("src/game_server/application/app_factory.py")]

    assert "import MODULE_ROUTERS" in app_factory
    assert "for router in MODULE_ROUTERS:" in app_factory
    assert "app.include_router(router)" in app_factory


def test_rendered_python_and_toml_are_valid() -> None:
    files = FastAPIProjectGenerator().render(project_specification())

    for path, content in files.items():
        if path.suffix == ".py":
            ast.parse(content)

    pyproject = tomllib.loads(files[PurePosixPath("pyproject.toml")])
    assert pyproject["project"]["name"] == "game_server"
    assert pyproject["project"]["requires-python"] == ">=3.12"
    assert "sqlalchemy>=2.0,<3" in pyproject["project"]["dependencies"]
    assert "asyncpg>=0.30,<1" in pyproject["project"]["dependencies"]
    assert "alembic>=1.18,<2" in pyproject["project"]["dependencies"]
    assert pyproject["project"]["optional-dependencies"]["test"] == [
        "httpx2",
        "pytest",
    ]
    assert pyproject["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]


def test_plan_matches_rendered_content_hashes() -> None:
    generator = FastAPIProjectGenerator()
    specification = project_specification()
    rendered_files = generator.render(specification)

    plan = generator.plan(specification)

    assert len(plan.files) == len(rendered_files)
    for planned_file in plan.files:
        content = rendered_files[planned_file.relative_path]
        assert planned_file.expected_content_hash == content_hash(content)


def test_readme_is_scaffolded_and_other_files_are_generated() -> None:
    plan = FastAPIProjectGenerator().plan(project_specification())
    ownership = {file.relative_path: file.ownership for file in plan.files}

    assert ownership[PurePosixPath("README.md")] is FileOwnership.SCAFFOLDED
    assert all(
        value is FileOwnership.GENERATED
        for path, value in ownership.items()
        if path != PurePosixPath("README.md")
    )


def test_same_specification_produces_same_render_and_plan() -> None:
    generator = FastAPIProjectGenerator()
    specification = project_specification()

    assert generator.render(specification) == generator.render(specification)
    assert generator.plan(specification) == generator.plan(specification)


def test_project_name_changes_related_content_hash() -> None:
    generator = FastAPIProjectGenerator()
    first_plan = generator.plan(project_specification(name="First Server"))
    second_plan = generator.plan(project_specification(name="Second Server"))
    app_factory_path = PurePosixPath("src/game_server/application/app_factory.py")

    first_file = next(
        file for file in first_plan.files if file.relative_path == app_factory_path
    )
    second_file = next(
        file for file in second_plan.files if file.relative_path == app_factory_path
    )

    assert first_file.expected_content_hash != second_file.expected_content_hash


def test_render_and_plan_do_not_write_files(tmp_path) -> None:
    before = set(tmp_path.rglob("*"))
    generator = FastAPIProjectGenerator()

    generator.render(project_specification())
    generator.plan(project_specification())

    assert set(tmp_path.rglob("*")) == before
