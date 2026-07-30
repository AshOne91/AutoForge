import sys
from dataclasses import dataclass

from autoforge.core.plugin import ValidatorPluginRegistry
from autoforge.services.generation import (
    FastAPIGeneratorPlugins,
    create_fastapi_generator_plugins,
)
from autoforge.services.validation import (
    ProcessRunner,
    ProjectValidationRequest,
    ProjectValidationResult,
    create_project_validator_plugins,
)


@dataclass(frozen=True, slots=True)
class BuiltinPluginCatalog:
    """AutoForge가 기본 제공하는 Plugin Registry 묶음."""

    generators: FastAPIGeneratorPlugins
    project_validators: ValidatorPluginRegistry[
        ProjectValidationRequest,
        ProjectValidationResult,
    ]


def create_builtin_plugin_catalog(
    package_name: str,
    process_runner: ProcessRunner,
    *,
    python_executable: str = sys.executable,
    validation_timeout_seconds: float = 30.0,
) -> BuiltinPluginCatalog:
    """명시적으로 주입받은 실행 의존성으로 기본 Plugin을 조립한다."""

    return BuiltinPluginCatalog(
        generators=create_fastapi_generator_plugins(package_name),
        project_validators=create_project_validator_plugins(
            process_runner,
            python_executable=python_executable,
            timeout_seconds=validation_timeout_seconds,
        ),
    )
