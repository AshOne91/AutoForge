import ast
import sys
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.generation import (
    FileOwnership,
    Generator,
    PlannedAction,
    content_hash,
)
from autoforge.core.specification import (
    EndpointDependency,
    EndpointSpec,
    FieldSpec,
    FieldType,
    FieldTypeKind,
    HttpMethod,
    ModelSpec,
    ModuleInfo,
    ModuleSpec,
    ResponseSpec,
    SchemaSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import (
    FastAPIModuleGenerator,
    GenerationPlanApplier,
    GenerationPlanResolver,
)


def tutorial_specification() -> ModuleSpec:
    return ModuleSpec(
        spec_version="1",
        module=ModuleInfo(
            name="tutorial",
            display_name="Tutorial",
            route_prefix="/api/tutorial",
        ),
        models=[
            ModelSpec(
                name="TutorialProgress",
                fields=[
                    FieldSpec(
                        name="current_step",
                        type=FieldType(kind=FieldTypeKind.INTEGER),
                    ),
                    FieldSpec(
                        name="completed",
                        type=FieldType(kind=FieldTypeKind.BOOLEAN),
                        default=False,
                    ),
                ],
            )
        ],
        endpoints=[
            EndpointSpec(
                name="get_progress",
                method=HttpMethod.GET,
                path="/progress",
                response=ResponseSpec(model="TutorialProgress"),
                handler="get_progress",
            ),
            EndpointSpec(
                name="complete_step",
                method=HttpMethod.POST,
                path="/complete",
                request=SchemaSpec(
                    fields=[
                        FieldSpec(
                            name="step",
                            type=FieldType(kind=FieldTypeKind.INTEGER),
                        )
                    ]
                ),
                response=ResponseSpec(
                    fields=[
                        FieldSpec(
                            name="progress",
                            type=FieldType(
                                kind=FieldTypeKind.MODEL,
                                reference="TutorialProgress",
                            ),
                        )
                    ]
                ),
                handler="complete_step",
            ),
        ],
    )


def test_module_generator_satisfies_protocol() -> None:
    generator: Generator[ModuleSpec] = FastAPIModuleGenerator("game_server")

    assert isinstance(generator, Generator)


def test_render_returns_generated_model_and_schema_files() -> None:
    files = FastAPIModuleGenerator("game_server").render(tutorial_specification())

    assert set(files) == {
        PurePosixPath("src/game_server/modules/tutorial/__init__.py"),
        PurePosixPath("src/game_server/modules/tutorial/handlers.py"),
        PurePosixPath("src/game_server/modules/tutorial/generated/__init__.py"),
        PurePosixPath("src/game_server/modules/tutorial/generated/models.py"),
        PurePosixPath("src/game_server/modules/tutorial/generated/router.py"),
        PurePosixPath("src/game_server/modules/tutorial/generated/schemas.py"),
    }


def test_rendered_models_and_schemas_are_valid_python() -> None:
    files = FastAPIModuleGenerator("game_server").render(tutorial_specification())
    models = files[
        PurePosixPath("src/game_server/modules/tutorial/generated/models.py")
    ]
    schemas = files[
        PurePosixPath("src/game_server/modules/tutorial/generated/schemas.py")
    ]

    ast.parse(models)
    ast.parse(schemas)
    assert "class TutorialProgress(BaseModel):" in models
    assert "current_step: int" in models
    assert "completed: bool = False" in models
    assert "class CompleteStepRequest(BaseModel):" in schemas
    assert "step: int" in schemas
    assert "class CompleteStepResponse(BaseModel):" in schemas
    assert "progress: TutorialProgress" in schemas


def test_plan_matches_rendered_files_and_marks_them_generated() -> None:
    generator = FastAPIModuleGenerator("game_server")
    specification = tutorial_specification()
    rendered = generator.render(specification)

    plan = generator.plan(specification)

    assert len(plan.files) == len(rendered)
    ownership = {file.relative_path: file.ownership for file in plan.files}
    assert (
        ownership[PurePosixPath("src/game_server/modules/tutorial/handlers.py")]
        is FileOwnership.SCAFFOLDED
    )
    assert all(
        value is FileOwnership.GENERATED
        for path, value in ownership.items()
        if path.name != "handlers.py"
    )
    for planned_file in plan.files:
        assert planned_file.expected_content_hash == content_hash(
            rendered[planned_file.relative_path]
        )


@pytest.mark.anyio
async def test_applied_model_and_schema_modules_can_be_imported(
    tmp_path: Path,
) -> None:
    generator = FastAPIModuleGenerator("game_server")
    specification = tutorial_specification()
    workspace = Workspace(tmp_path)
    rendered = generator.render(specification)
    resolved = GenerationPlanResolver().resolve(
        generator.plan(specification),
        workspace,
    )
    GenerationPlanApplier().apply(
        job_id="module-job",
        plan=resolved,
        rendered_files=rendered,
        workspace=workspace,
    )

    import_code = (
        "import sys; sys.path.insert(0, 'src'); "
        "from game_server.modules.tutorial.generated.models "
        "import TutorialProgress; "
        "from game_server.modules.tutorial.generated.schemas "
        "import CompleteStepRequest; "
        "from game_server.modules.tutorial.generated.router import router"
    )
    command = (sys.executable, "-c", import_code)
    result = await AsyncioProcessRunner().run(
        command,
        cwd=workspace.root,
        timeout_seconds=10,
    )

    assert result.succeeded, result.stderr


def test_same_module_specification_is_deterministic() -> None:
    generator = FastAPIModuleGenerator("game_server")
    specification = tutorial_specification()

    assert generator.render(specification) == generator.render(specification)
    assert generator.plan(specification) == generator.plan(specification)


def test_router_calls_async_handlers_with_schema_types() -> None:
    files = FastAPIModuleGenerator("game_server").render(tutorial_specification())
    router = files[
        PurePosixPath("src/game_server/modules/tutorial/generated/router.py")
    ]
    handlers = files[PurePosixPath("src/game_server/modules/tutorial/handlers.py")]

    ast.parse(router)
    ast.parse(handlers)
    assert 'router = APIRouter(prefix="/api/tutorial", tags=["Tutorial"])' in router
    assert '@router.get("/progress", response_model=TutorialProgress)' in router
    assert "return await handlers.get_progress()" in router
    assert '@router.post("/complete", response_model=CompleteStepResponse)' in router
    assert "request: CompleteStepRequest" in router
    assert "return await handlers.complete_step(request)" in router
    assert "async def get_progress() -> TutorialProgress:" in handlers
    assert "request: CompleteStepRequest" in handlers
    assert "raise NotImplementedError" in handlers


def test_session_store_dependency_is_injected_into_handler() -> None:
    specification = tutorial_specification()
    dependent_endpoint = specification.endpoints[1].model_copy(
        update={"dependencies": [EndpointDependency.SESSION_STORE]}
    )
    specification = specification.model_copy(
        update={"endpoints": [specification.endpoints[0], dependent_endpoint]}
    )

    files = FastAPIModuleGenerator("game_server").render(specification)
    router = files[
        PurePosixPath("src/game_server/modules/tutorial/generated/router.py")
    ]
    handlers = files[
        PurePosixPath("src/game_server/modules/tutorial/handlers.py")
    ]

    ast.parse(router)
    ast.parse(handlers)
    assert "from fastapi import APIRouter, Depends" in router
    assert (
        "session_store: Annotated[SessionStore, Depends(get_session_store)]" in router
    )
    assert "handlers.complete_step(request, session_store)" in router
    assert "session_store: SessionStore," in handlers


def test_database_session_registry_dependency_is_injected_into_handler() -> None:
    specification = tutorial_specification()
    dependent_endpoint = specification.endpoints[1].model_copy(
        update={
            "dependencies": [EndpointDependency.DATABASE_SESSION_REGISTRY]
        }
    )
    specification = specification.model_copy(
        update={"endpoints": [specification.endpoints[0], dependent_endpoint]}
    )

    files = FastAPIModuleGenerator("game_server").render(specification)
    router = files[
        PurePosixPath("src/game_server/modules/tutorial/generated/router.py")
    ]
    handlers = files[
        PurePosixPath("src/game_server/modules/tutorial/handlers.py")
    ]

    ast.parse(router)
    ast.parse(handlers)
    assert "from fastapi import APIRouter, Depends" in router
    assert (
        "session_registry: Annotated[AsyncSessionRegistry, "
        "Depends(get_session_registry)]" in router
    )
    assert "handlers.complete_step(request, session_registry)" in router
    assert "session_registry: AsyncSessionRegistry," in handlers


def test_same_specification_preserves_modified_handler(tmp_path: Path) -> None:
    generator = FastAPIModuleGenerator("game_server")
    specification = tutorial_specification()
    workspace = Workspace(tmp_path)
    rendered = generator.render(specification)
    first_plan = GenerationPlanResolver().resolve(
        generator.plan(specification),
        workspace,
    )
    GenerationPlanApplier().apply(
        job_id="first-module-job",
        plan=first_plan,
        rendered_files=rendered,
        workspace=workspace,
    )
    handler_path = tmp_path / "src/game_server/modules/tutorial/handlers.py"
    handler_path.write_text("# user implementation\n", encoding="utf-8")

    second_plan = GenerationPlanResolver().resolve(
        generator.plan(specification),
        workspace,
    )
    second_manifest = GenerationPlanApplier().apply(
        job_id="second-module-job",
        plan=second_plan,
        rendered_files=rendered,
        workspace=workspace,
    )

    assert handler_path.read_text(encoding="utf-8") == "# user implementation\n"
    handler_result = next(
        file
        for file in second_manifest.files
        if file.relative_path.name == "handlers.py"
    )
    assert handler_result.status.value == "preserved"


def test_endpoint_addition_preserves_handler_but_conflicts_generated_files(
    tmp_path: Path,
) -> None:
    generator = FastAPIModuleGenerator("game_server")
    original = tutorial_specification()
    workspace = Workspace(tmp_path)
    rendered = generator.render(original)
    GenerationPlanApplier().apply(
        job_id="first-module-job",
        plan=GenerationPlanResolver().resolve(
            generator.plan(original),
            workspace,
        ),
        rendered_files=rendered,
        workspace=workspace,
    )
    handler_path = tmp_path / "src/game_server/modules/tutorial/handlers.py"
    handler_path.write_text("# user implementation\n", encoding="utf-8")
    added_endpoint = EndpointSpec(
        name="reset_progress",
        method=HttpMethod.DELETE,
        path="/progress",
        response=ResponseSpec(model="TutorialProgress"),
        handler="reset_progress",
    )
    changed = original.model_copy(
        update={"endpoints": [*original.endpoints, added_endpoint]}
    )

    resolved = GenerationPlanResolver().resolve(
        generator.plan(changed),
        workspace,
    )
    actions = {file.relative_path.name: file.action for file in resolved.files}

    assert actions["handlers.py"] is PlannedAction.KEEP
    assert actions["router.py"] is PlannedAction.CONFLICT
    assert handler_path.read_text(encoding="utf-8") == "# user implementation\n"


def test_endpoint_addition_replaces_manifest_owned_files_and_preserves_handler(
    tmp_path: Path,
) -> None:
    generator = FastAPIModuleGenerator("game_server")
    original = tutorial_specification()
    workspace = Workspace(tmp_path)
    original_rendered = generator.render(original)
    previous_manifest = GenerationPlanApplier().apply(
        job_id="first-module-job",
        plan=GenerationPlanResolver().resolve(
            generator.plan(original),
            workspace,
        ),
        rendered_files=original_rendered,
        workspace=workspace,
    )
    handler_path = tmp_path / "src/game_server/modules/tutorial/handlers.py"
    handler_path.write_text("# user implementation\n", encoding="utf-8")
    added_endpoint = EndpointSpec(
        name="reset_progress",
        method=HttpMethod.DELETE,
        path="/progress",
        response=ResponseSpec(model="TutorialProgress"),
        handler="reset_progress",
    )
    changed = original.model_copy(
        update={"endpoints": [*original.endpoints, added_endpoint]}
    )
    changed_rendered = generator.render(changed)
    resolved = GenerationPlanResolver().resolve(
        generator.plan(changed),
        workspace,
        manifest=previous_manifest,
    )

    manifest = GenerationPlanApplier().apply(
        job_id="second-module-job",
        plan=resolved,
        rendered_files=changed_rendered,
        workspace=workspace,
    )

    router_path = tmp_path / "src/game_server/modules/tutorial/generated/router.py"
    assert "@router.delete" in router_path.read_text(encoding="utf-8")
    assert handler_path.read_text(encoding="utf-8") == "# user implementation\n"
    results = {file.relative_path.name: file.status for file in manifest.files}
    assert results["router.py"].value == "changed"
    assert results["handlers.py"].value == "preserved"
