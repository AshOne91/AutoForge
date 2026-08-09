from pathlib import PurePosixPath

from autoforge.core.generation import FileOwnership, Generator, content_hash
from autoforge.core.specification import ApplicationSpec, ProjectInfo, ProjectSpec
from autoforge.services.generation import DockerfileGenerator


def project_specification(*, enabled: bool = False) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
            description="모듈형 FastAPI 게임 서버",
        ),
        application=ApplicationSpec(),
        tooling={"docker": {"enabled": enabled}},
    )


def test_dockerfile_generator_satisfies_protocol() -> None:
    generator: Generator[ProjectSpec] = DockerfileGenerator()

    assert isinstance(generator, Generator)


def test_render_is_empty_until_enabled() -> None:
    files = DockerfileGenerator().render(project_specification())

    assert files == {}


def test_render_creates_expected_dockerfile_when_enabled() -> None:
    files = DockerfileGenerator().render(project_specification(enabled=True))

    dockerfile = files[PurePosixPath("Dockerfile")]

    assert "FROM python:3.12-slim" in dockerfile
    assert "WORKDIR /app" in dockerfile
    assert "COPY src ./src" in dockerfile
    assert 'RUN pip install --no-cache-dir ".[test]"' in dockerfile
    assert 'CMD ["uvicorn", "game_server.main:app"' in dockerfile
    assert "secret" not in dockerfile.lower()
    assert "deploy" not in dockerfile.lower()


def test_plan_matches_rendered_content_hashes() -> None:
    generator = DockerfileGenerator()
    specification = project_specification(enabled=True)
    rendered_files = generator.render(specification)

    plan = generator.plan(specification)

    assert len(plan.files) == len(rendered_files)
    for planned_file in plan.files:
        content = rendered_files[planned_file.relative_path]
        assert planned_file.ownership is FileOwnership.GENERATED
        assert planned_file.expected_content_hash == content_hash(content)


def test_same_specification_produces_same_render_and_plan() -> None:
    generator = DockerfileGenerator()
    specification = project_specification(enabled=True)

    assert generator.render(specification) == generator.render(specification)
    assert generator.plan(specification) == generator.plan(specification)
