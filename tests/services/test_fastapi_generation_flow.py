import sys
from pathlib import Path

import pytest

from autoforge.core.specification import (
    ApplicationSpec,
    EndpointSpec,
    FieldSpec,
    FieldType,
    FieldTypeKind,
    HttpMethod,
    ModelSpec,
    ModuleInfo,
    ModuleSpec,
    ProjectInfo,
    ProjectSpec,
    ResponseSpec,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import (
    DockerfileGenerator,
    FastAPIModuleGenerator,
    FastAPIProjectGenerator,
    GenerationPlanApplier,
    GenerationPlanResolver,
)
from autoforge.services.validation import ProjectValidator


def project_specification() -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
            description="모듈형 FastAPI 게임 서버",
        ),
        application=ApplicationSpec(modules=["tutorial"]),
        tooling={"docker": {"enabled": True}},
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
            )
        ],
    )


def apply_generator(
    generator: FastAPIProjectGenerator | FastAPIModuleGenerator,
    specification: ProjectSpec | ModuleSpec,
    workspace: Workspace,
) -> None:
    rendered = generator.render(specification)
    plan = GenerationPlanResolver().resolve(
        generator.plan(specification),
        workspace,
    )
    GenerationPlanApplier().apply(
        job_id=f"{generator.generator_id}-job",
        plan=plan,
        rendered_files=rendered,
        workspace=workspace,
    )


@pytest.mark.anyio
async def test_generated_tutorial_router_is_registered_and_callable(
    tmp_path: Path,
) -> None:
    workspace = Workspace(tmp_path)
    apply_generator(
        FastAPIProjectGenerator(),
        project_specification(),
        workspace,
    )
    apply_generator(
        FastAPIModuleGenerator("game_server"),
        tutorial_specification(),
        workspace,
    )
    handlers = tmp_path / "src/game_server/modules/tutorial/handlers.py"
    handlers.write_text(
        "from game_server.modules.tutorial.generated.models "
        "import TutorialProgress\n"
        "\n"
        "\n"
        "async def get_progress() -> TutorialProgress:\n"
        "    return TutorialProgress(current_step=2, completed=False)\n",
        encoding="utf-8",
    )

    validation = await ProjectValidator(
        AsyncioProcessRunner(),
        timeout_seconds=30,
    ).validate(
        package_name="game_server",
        workspace=workspace,
    )
    endpoint_code = (
        "import sys; "
        "sys.path.insert(0, 'src'); "
        "from fastapi.testclient import TestClient; "
        "from game_server.main import app; "
        "response = TestClient(app).get('/api/tutorial/progress'); "
        "assert response.status_code == 200, response.text; "
        "assert response.json() == "
        "{'current_step': 2, 'completed': False}"
    )
    endpoint_result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", endpoint_code),
        cwd=workspace.root,
        timeout_seconds=30,
    )

    assert validation.succeeded
    assert endpoint_result.succeeded, (
        endpoint_result.stdout,
        endpoint_result.stderr,
    )


def test_generated_project_has_a_complete_docker_build_context(
    tmp_path: Path,
) -> None:
    workspace = Workspace(tmp_path)
    apply_generator(FastAPIProjectGenerator(), project_specification(), workspace)
    apply_generator(DockerfileGenerator(), project_specification(), workspace)

    dockerfile = (tmp_path / "Dockerfile").read_text(encoding="utf-8")

    assert (tmp_path / "pyproject.toml").is_file()
    assert (tmp_path / "README.md").is_file()
    assert (tmp_path / "src/game_server").is_dir()
    assert "COPY pyproject.toml README.md ./" in dockerfile
    assert "COPY src ./src" in dockerfile
    assert 'CMD ["uvicorn", "game_server.main:app"' in dockerfile
