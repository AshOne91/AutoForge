from pathlib import PurePosixPath

from autoforge.core.generation import FileOwnership, Generator, content_hash
from autoforge.core.specification import (
    ApplicationSpec,
    DatabaseStoreSpec,
    ProjectInfo,
    ProjectSpec,
)
from autoforge.services.generation import DockerfileGenerator


def project_specification(
    *,
    enabled: bool = False,
    has_database: bool = False,
    local_application_enabled: bool = False,
) -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
            description="모듈형 FastAPI 게임 서버",
        ),
        application=ApplicationSpec(
            databases=[
                DatabaseStoreSpec(name="identity", global_url_env="IDENTITY_DATABASE_URL")
            ]
            if has_database
            else []
        ),
        tooling={
            "docker": {"enabled": enabled},
            "local_environment": {
                "enabled": local_application_enabled,
                "application_enabled": local_application_enabled,
            },
        },
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
    assert 'RUN pip install --no-cache-dir .' in dockerfile
    assert 'CMD ["python", "-m", "uvicorn", "game_server.main:app"' in dockerfile
    assert "secret" not in dockerfile.lower()
    assert "deploy" not in dockerfile.lower()


def test_render_creates_dockerfile_for_local_application_runtime() -> None:
    files = DockerfileGenerator().render(
        project_specification(local_application_enabled=True)
    )

    assert PurePosixPath("Dockerfile") in files


def test_render_includes_migration_files_for_database_projects() -> None:
    dockerfile = DockerfileGenerator().render(
        project_specification(enabled=True, has_database=True)
    )[PurePosixPath("Dockerfile")]

    assert "COPY alembic.ini ./" in dockerfile
    assert "COPY migrations ./migrations" in dockerfile
    assert "COPY scripts ./scripts" in dockerfile
    assert "COPY src ./src\nCOPY alembic.ini ./" in dockerfile


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
