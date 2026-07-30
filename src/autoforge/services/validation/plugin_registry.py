import sys
from typing import Final

from autoforge.core.plugin import (
    PluginCapability,
    PluginMetadata,
    PluginPermission,
    ValidatorPluginAdapter,
    ValidatorPluginRegistry,
)
from autoforge.services.validation.models import (
    ProcessRunner,
    ProjectValidationRequest,
    ProjectValidationResult,
)
from autoforge.services.validation.project_validator import ProjectValidator

PROJECT_VALIDATOR_ID: Final = "autoforge.validator.python.project"
PROJECT_VALIDATOR_VERSION: Final = "0.1.0"


def create_project_validator_plugins(
    process_runner: ProcessRunner,
    *,
    python_executable: str = sys.executable,
    timeout_seconds: float = 30.0,
) -> ValidatorPluginRegistry[ProjectValidationRequest, ProjectValidationResult]:
    validator = ProjectValidator(
        process_runner,
        python_executable=python_executable,
        timeout_seconds=timeout_seconds,
    )

    async def validate(
        request: ProjectValidationRequest,
    ) -> ProjectValidationResult:
        return await validator.validate(
            package_name=request.package_name,
            workspace=request.workspace,
        )

    registry = ValidatorPluginRegistry[
        ProjectValidationRequest,
        ProjectValidationResult,
    ]()
    registry.register(
        ValidatorPluginAdapter(
            validator_id=PROJECT_VALIDATOR_ID,
            validator_version=PROJECT_VALIDATOR_VERSION,
            validate=validate,
            metadata=PluginMetadata(
                name=PROJECT_VALIDATOR_ID,
                version=PROJECT_VALIDATOR_VERSION,
                description="Python 프로젝트 Import, Test, Lint와 Build Validator",
                capabilities=(PluginCapability.VALIDATOR,),
                permissions=(
                    PluginPermission.FILESYSTEM_READ,
                    PluginPermission.FILESYSTEM_WRITE,
                    PluginPermission.PROCESS_EXECUTE,
                ),
            ),
        )
    )
    return registry
