from pathlib import PurePosixPath

from autoforge.core.generation import FileOwnership
from autoforge.core.specification import (
    ApplicationSpec,
    CiProvider,
    CiSpec,
    CiWorkflow,
    ProjectInfo,
    ProjectSpec,
    ToolingSpec,
)
from autoforge.services.generation.ci import CIGenerator


def _specification(providers: list[CiProvider]) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server", package_name="game_server", version="0.1.0"
        ),
        application=ApplicationSpec(),
        tooling=ToolingSpec(
            ci=CiSpec(
                providers=providers, workflows=[CiWorkflow.TEST, CiWorkflow.BUILD]
            )
        ),
    )


def test_ci_generator_renders_least_privilege_github_actions_and_jenkins() -> None:
    generator = CIGenerator()
    rendered = generator.render(
        _specification([CiProvider.GITHUB_ACTIONS, CiProvider.JENKINS])
    )

    github = rendered[PurePosixPath(".github/workflows/ci.yml")]
    jenkins = rendered[PurePosixPath("Jenkinsfile")]
    assert "contents: read" in github
    assert "python -m pytest" in github
    assert "pip wheel --no-deps" in github
    assert "deploy" not in github.lower()
    assert "credential" not in jenkins.lower()
    assert "python -m ruff check ." in jenkins

    plan = generator.plan(_specification([CiProvider.GITHUB_ACTIONS]))
    assert plan.files[0].ownership is FileOwnership.GENERATED
