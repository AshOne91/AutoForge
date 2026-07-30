from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProcessResult:
    command: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and self.error is None


class ProcessRunner(Protocol):
    async def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float,
    ) -> ProcessResult: ...


class ValidationStep(StrEnum):
    IMPORT = "import"
    PYTEST = "pytest"


@dataclass(frozen=True, slots=True)
class ValidationStepResult:
    step: ValidationStep
    process: ProcessResult

    @property
    def succeeded(self) -> bool:
        return self.process.succeeded


@dataclass(frozen=True, slots=True)
class ProjectValidationResult:
    steps: tuple[ValidationStepResult, ...]

    @property
    def succeeded(self) -> bool:
        return bool(self.steps) and all(step.succeeded for step in self.steps)
