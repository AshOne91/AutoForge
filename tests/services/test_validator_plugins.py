from pathlib import Path

import pytest

from autoforge.core.plugin import PluginPermission
from autoforge.core.workspace import Workspace
from autoforge.services.validation import (
    PROJECT_VALIDATOR_ID,
    ProcessResult,
    ProjectValidationRequest,
    ValidationStep,
    create_project_validator_plugins,
)


class StubProcessRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    async def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.commands.append(command)
        return ProcessResult(
            command=command,
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            duration_seconds=0.01,
        )


@pytest.mark.anyio
async def test_project_validator_plugin_runs_all_validation_steps(
    tmp_path: Path,
) -> None:
    runner = StubProcessRunner()
    registry = create_project_validator_plugins(
        runner,
        python_executable="python",
    )
    plugin = registry.get(PROJECT_VALIDATOR_ID)

    result = await plugin.validate(
        ProjectValidationRequest(
            package_name="game_server",
            workspace=Workspace(tmp_path),
        )
    )

    assert result.succeeded
    assert [step.step for step in result.steps] == [
        ValidationStep.IMPORT,
        ValidationStep.PYTEST,
        ValidationStep.RUFF,
        ValidationStep.PACKAGE_BUILD,
    ]
    assert len(runner.commands) == 4


def test_project_validator_plugin_declares_required_permissions() -> None:
    plugin = create_project_validator_plugins(StubProcessRunner()).get(
        PROJECT_VALIDATOR_ID
    )

    assert plugin.metadata.permissions == (
        PluginPermission.FILESYSTEM_READ,
        PluginPermission.FILESYSTEM_WRITE,
        PluginPermission.PROCESS_EXECUTE,
    )


def test_project_validator_registry_rejects_duplicate_id() -> None:
    registry = create_project_validator_plugins(StubProcessRunner())
    duplicate = create_project_validator_plugins(StubProcessRunner()).get(
        PROJECT_VALIDATOR_ID
    )

    with pytest.raises(ValueError, match="already registered"):
        registry.register(duplicate)
