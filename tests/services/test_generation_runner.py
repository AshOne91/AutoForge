from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.specification import ApplicationSpec, ProjectInfo, ProjectSpec
from autoforge.core.workspace import Workspace
from autoforge.services.generation import (
    FastAPIProjectGenerator,
    GenerationRunner,
    GenerationRunnerError,
    SQLAlchemyInfrastructureGenerator,
)


def project_specification() -> ProjectSpec:
    return ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="KIS Auto Trading",
            package_name="kis_auto_trading",
            version="0.1.0",
        ),
        application=ApplicationSpec(modules=[]),
    )


def test_runner_composes_and_applies_multiple_generators(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    manifest = GenerationRunner[ProjectSpec]().run(
        job_id="project-generation",
        specification=project_specification(),
        generators=[
            FastAPIProjectGenerator(),
            SQLAlchemyInfrastructureGenerator(),
        ],
        workspace=workspace,
    )

    paths = {file.relative_path for file in manifest.files}
    assert PurePosixPath("src/kis_auto_trading/main.py") in paths
    assert (
        PurePosixPath("src/kis_auto_trading/infrastructure/database/session.py")
        in paths
    )
    assert (tmp_path / "src/kis_auto_trading/main.py").is_file()
    assert (
        tmp_path / "src/kis_auto_trading/infrastructure/database/session.py"
    ).is_file()


def test_runner_rejects_duplicate_output_before_writing(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    generator = FastAPIProjectGenerator()

    with pytest.raises(GenerationRunnerError, match="same path"):
        GenerationRunner[ProjectSpec]().run(
            job_id="duplicate-generation",
            specification=project_specification(),
            generators=[generator, generator],
            workspace=workspace,
        )

    assert list(tmp_path.iterdir()) == []


def test_runner_requires_at_least_one_generator(tmp_path: Path) -> None:
    with pytest.raises(GenerationRunnerError, match="At least one"):
        GenerationRunner[ProjectSpec]().run(
            job_id="empty-generation",
            specification=project_specification(),
            generators=[],
            workspace=Workspace(tmp_path),
        )
