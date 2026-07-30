from pathlib import Path

import pytest

from autoforge.core.generation import content_hash
from autoforge.core.specification import ApplicationSpec, ProjectInfo, ProjectSpec
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.generation import (
    FastAPIProjectGenerator,
    GenerationPlanApplier,
    GenerationPlanResolver,
)
from autoforge.services.validation import (
    ProcessResult,
    ProjectValidator,
    ValidationStep,
)


class StubProcessRunner:
    def __init__(self, results: list[ProcessResult]) -> None:
        self._results = iter(results)
        self.commands: list[tuple[str, ...]] = []
        self.working_directories: list[Path] = []

    async def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.commands.append(command)
        self.working_directories.append(cwd)
        return next(self._results)


def process_result(*, exit_code: int = 0) -> ProcessResult:
    return ProcessResult(
        command=("python",),
        exit_code=exit_code,
        stdout="",
        stderr="",
        timed_out=False,
        duration_seconds=0.01,
    )


@pytest.mark.anyio
async def test_validator_runs_import_then_pytest(tmp_path: Path) -> None:
    runner = StubProcessRunner([process_result(), process_result()])
    workspace = Workspace(tmp_path)

    result = await ProjectValidator(
        runner,
        python_executable="python",
    ).validate(
        package_name="game_server",
        workspace=workspace,
    )

    assert result.succeeded, [
        (
            step.step,
            step.process.exit_code,
            step.process.stdout,
            step.process.stderr,
        )
        for step in result.steps
    ]
    assert [step.step for step in result.steps] == [
        ValidationStep.IMPORT,
        ValidationStep.PYTEST,
    ]
    assert runner.commands[1] == ("python", "-m", "pytest")
    assert runner.working_directories == [workspace.root, workspace.root]


@pytest.mark.anyio
async def test_validator_stops_after_import_failure(tmp_path: Path) -> None:
    runner = StubProcessRunner([process_result(exit_code=1)])

    result = await ProjectValidator(runner).validate(
        package_name="game_server",
        workspace=Workspace(tmp_path),
    )

    assert not result.succeeded
    assert len(result.steps) == 1
    assert result.steps[0].step is ValidationStep.IMPORT
    assert len(runner.commands) == 1


@pytest.mark.anyio
async def test_generated_fastapi_project_passes_real_validation(
    tmp_path: Path,
) -> None:
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
            description="모듈형 FastAPI 게임 서버",
        ),
        application=ApplicationSpec(),
    )
    workspace = Workspace(tmp_path)
    generator = FastAPIProjectGenerator()
    rendered = generator.render(specification)
    resolved = GenerationPlanResolver().resolve(
        generator.plan(specification),
        workspace,
    )
    GenerationPlanApplier().apply(
        job_id=content_hash("job"),
        plan=resolved,
        rendered_files=rendered,
        workspace=workspace,
    )

    result = await ProjectValidator(
        AsyncioProcessRunner(),
        timeout_seconds=30,
    ).validate(
        package_name="game_server",
        workspace=workspace,
    )

    assert result.succeeded, [
        (
            step.step,
            step.process.exit_code,
            step.process.stdout,
            step.process.stderr,
        )
        for step in result.steps
    ]
    assert [step.step for step in result.steps] == [
        ValidationStep.IMPORT,
        ValidationStep.PYTEST,
    ]
    assert "1 passed" in result.steps[1].process.stdout


def test_validation_result_requires_successful_steps() -> None:
    from autoforge.services.validation import ProjectValidationResult

    assert not ProjectValidationResult(steps=()).succeeded


@pytest.mark.anyio
async def test_import_command_does_not_accept_unsafe_package_name(
    tmp_path: Path,
) -> None:
    validator = ProjectValidator(StubProcessRunner([]))

    with pytest.raises(ValueError):
        await validator.validate(
            package_name="game_server; malicious",
            workspace=Workspace(tmp_path),
        )
