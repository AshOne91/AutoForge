import sys

from autoforge.core.specification.naming import validate_python_name
from autoforge.core.workspace import Workspace
from autoforge.services.validation.models import (
    ProcessRunner,
    ProjectValidationResult,
    ValidationStep,
    ValidationStepResult,
)


class ProjectValidator:
    """생성된 Python 프로젝트의 Import, 테스트, lint와 build를 검증한다."""

    def __init__(
        self,
        process_runner: ProcessRunner,
        *,
        python_executable: str = sys.executable,
        timeout_seconds: float = 30.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Timeout은 0보다 커야 합니다.")
        self._process_runner = process_runner
        self._python_executable = python_executable
        self._timeout_seconds = timeout_seconds

    async def validate(
        self,
        *,
        package_name: str,
        workspace: Workspace,
    ) -> ProjectValidationResult:
        validated_package_name = validate_python_name(package_name)
        import_result = await self._process_runner.run(
            self._import_command(validated_package_name),
            cwd=workspace.root,
            timeout_seconds=self._timeout_seconds,
        )
        steps = [
            ValidationStepResult(
                step=ValidationStep.IMPORT,
                process=import_result,
            )
        ]
        if not import_result.succeeded:
            return ProjectValidationResult(steps=tuple(steps))

        commands = (
            (
                ValidationStep.PYTEST,
                (self._python_executable, "-m", "pytest"),
            ),
            (
                ValidationStep.RUFF,
                (self._python_executable, "-m", "ruff", "check", "."),
            ),
            (
                ValidationStep.PACKAGE_BUILD,
                (
                    self._python_executable,
                    "-m",
                    "pip",
                    "wheel",
                    "--no-deps",
                    "--no-build-isolation",
                    "--wheel-dir",
                    ".autoforge/dist",
                    ".",
                ),
            ),
        )
        for step, command in commands:
            process_result = await self._process_runner.run(
                command,
                cwd=workspace.root,
                timeout_seconds=self._timeout_seconds,
            )
            steps.append(ValidationStepResult(step=step, process=process_result))
            if not process_result.succeeded:
                break
        return ProjectValidationResult(steps=tuple(steps))

    def _import_command(self, package_name: str) -> tuple[str, ...]:
        code = f"import sys; sys.path.insert(0, 'src'); import {package_name}.main"
        return self._python_executable, "-c", code
