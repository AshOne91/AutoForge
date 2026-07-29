import pytest
from pydantic import ValidationError

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
    SchemaSpec,
)


def test_create_minimal_project_spec() -> None:
    spec = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(modules=["tutorial"]),
    )

    assert spec.project.package_name == "game_server"
    assert spec.application.framework == "fastapi"
    assert spec.application.modules == ["tutorial"]


def test_create_tutorial_module_spec() -> None:
    progress_model = ModelSpec(
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
    endpoint = EndpointSpec(
        name="get_progress",
        method=HttpMethod.GET,
        path="/progress",
        response=ResponseSpec(model="TutorialProgress"),
        handler="get_progress",
    )

    spec = ModuleSpec(
        spec_version="1",
        module=ModuleInfo(
            name="tutorial",
            display_name="Tutorial",
            route_prefix="/api/tutorial",
        ),
        models=[progress_model],
        endpoints=[endpoint],
    )

    assert spec.module.name == "tutorial"
    assert spec.endpoints[0].response.model_name == "TutorialProgress"


@pytest.mark.parametrize(
    "name",
    [
        "GameServer",
        "2server",
        "game-server",
        "game server",
        "../server",
        "class",
        "__server",
        "nul",
    ],
)
def test_project_spec_rejects_invalid_package_name(name: str) -> None:
    with pytest.raises(ValidationError):
        ProjectInfo(name="Game Server", package_name=name, version="0.1.0")


def test_project_spec_rejects_unsupported_version_and_framework() -> None:
    with pytest.raises(ValidationError):
        ProjectSpec(
            spec_version="2",
            project=ProjectInfo(
                name="Game Server",
                package_name="game_server",
                version="0.1.0",
            ),
            application={"framework": "django"},
        )


@pytest.mark.parametrize("path", ["progress", "/a//b", "/../secret", r"/a\b"])
def test_endpoint_rejects_invalid_http_path(path: str) -> None:
    with pytest.raises(ValidationError):
        EndpointSpec(
            name="get_progress",
            method=HttpMethod.GET,
            path=path,
            response=ResponseSpec(),
            handler="get_progress",
        )


def test_module_spec_rejects_duplicate_models_and_endpoints() -> None:
    model = ModelSpec(name="TutorialProgress")
    endpoint = EndpointSpec(
        name="get_progress",
        method=HttpMethod.GET,
        path="/progress",
        response=ResponseSpec(model="TutorialProgress"),
        handler="get_progress",
    )

    with pytest.raises(ValidationError, match="Model 이름은 중복"):
        ModuleSpec(
            spec_version="1",
            module=ModuleInfo(
                name="tutorial",
                display_name="Tutorial",
                route_prefix="/api/tutorial",
            ),
            models=[model, model],
        )

    with pytest.raises(ValidationError, match="Endpoint 이름은 중복"):
        ModuleSpec(
            spec_version="1",
            module=ModuleInfo(
                name="tutorial",
                display_name="Tutorial",
                route_prefix="/api/tutorial",
            ),
            models=[model],
            endpoints=[endpoint, endpoint],
        )


def test_module_spec_rejects_unknown_model_reference() -> None:
    endpoint = EndpointSpec(
        name="get_progress",
        method=HttpMethod.GET,
        path="/progress",
        request=SchemaSpec(
            fields=[
                FieldSpec(
                    name="progress",
                    type=FieldType(
                        kind=FieldTypeKind.MODEL,
                        reference="MissingModel",
                    ),
                )
            ]
        ),
        response=ResponseSpec(),
        handler="get_progress",
    )

    with pytest.raises(ValidationError, match="정의되지 않은 Model"):
        ModuleSpec(
            spec_version="1",
            module=ModuleInfo(
                name="tutorial",
                display_name="Tutorial",
                route_prefix="/api/tutorial",
            ),
            endpoints=[endpoint],
        )
