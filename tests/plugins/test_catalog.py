from pathlib import Path

import pytest

from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.plugins import create_builtin_plugin_catalog
from autoforge.services.generation.fastapi_module import MODULE_GENERATOR_ID
from autoforge.services.generation.fastapi_project import GENERATOR_ID
from autoforge.services.validation import (
    PROJECT_VALIDATOR_ID,
    ProcessResult,
    ProjectValidationRequest,
)


class StubProcessRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.timeouts: list[float] = []

    async def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float,
    ) -> ProcessResult:
        self.commands.append(command)
        self.timeouts.append(timeout_seconds)
        return ProcessResult(
            command=command,
            exit_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            duration_seconds=0.0,
        )


def test_builtin_catalog_contains_expected_plugins() -> None:
    catalog = create_builtin_plugin_catalog("sample_server", StubProcessRunner())

    assert catalog.generators.project.names() == [GENERATOR_ID]
    assert catalog.generators.module.names() == [MODULE_GENERATOR_ID]
    assert catalog.project_validators.names() == [PROJECT_VALIDATOR_ID]


@pytest.mark.anyio
async def test_builtin_catalog_uses_explicit_dependencies(tmp_path: Path) -> None:
    runner = StubProcessRunner()
    catalog = create_builtin_plugin_catalog(
        "sample_server",
        runner,
        python_executable="custom-python",
        validation_timeout_seconds=12.5,
    )

    result = await catalog.project_validators.get(PROJECT_VALIDATOR_ID).validate(
        ProjectValidationRequest(
            package_name="sample_server",
            workspace=Workspace(tmp_path),
        )
    )

    assert result.succeeded
    assert runner.commands[0][0] == "custom-python"
    assert runner.timeouts == [12.5] * 4


def test_builtin_catalog_does_not_share_mutable_registries() -> None:
    first = create_builtin_plugin_catalog("first_server", StubProcessRunner())
    second = create_builtin_plugin_catalog("second_server", StubProcessRunner())

    first.generators.project.unregister(GENERATOR_ID)
    first.project_validators.unregister(PROJECT_VALIDATOR_ID)

    assert second.generators.project.exists(GENERATOR_ID)
    assert second.project_validators.exists(PROJECT_VALIDATOR_ID)


def test_builtin_catalog_accepts_production_process_runner() -> None:
    catalog = create_builtin_plugin_catalog(
        "sample_server",
        AsyncioProcessRunner(),
    )

    assert catalog.project_validators.exists(PROJECT_VALIDATOR_ID)
