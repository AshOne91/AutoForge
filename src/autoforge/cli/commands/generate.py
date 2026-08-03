import asyncio
from pathlib import Path
from typing import Annotated

import typer

from autoforge.application.generation import (
    GenerationJobPipeline,
    GenerationJobRequest,
    GenerationSpecificationError,
)
from autoforge.application.generation.pipeline import (
    validate_database_placements,
    validate_endpoint_dependencies,
)
from autoforge.core.event import EventBus
from autoforge.core.pipeline import PipelineExecutionError
from autoforge.core.specification import ModuleSpec, ProjectSpec
from autoforge.infrastructure.job import InMemoryJobStore
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.services.validation import ProjectValidator

app = typer.Typer()


@app.callback(invoke_without_command=True)
def generate(
    project: Annotated[Path, typer.Option(exists=True)] = Path("autoforge.yaml"),
    specifications: Annotated[Path, typer.Option(exists=True)] = Path(
        "specifications"
    ),
    output: Annotated[Path, typer.Option()] = Path("."),
) -> None:
    """명세로 프로젝트를 생성하고 검증 Pipeline을 실행한다."""

    pipeline = GenerationJobPipeline(
        job_store=InMemoryJobStore(),
        event_bus=EventBus(),
        validator=ProjectValidator(AsyncioProcessRunner()),
    )
    try:
        execution = asyncio.run(
            pipeline.run(
                GenerationJobRequest(
                    project_path=project,
                    specifications_path=specifications,
                    output_path=output,
                )
            )
        )
    except PipelineExecutionError as error:
        cause = error.__cause__
        if isinstance(cause, GenerationSpecificationError):
            raise typer.BadParameter(str(cause)) from cause
        detail = str(cause) if cause is not None else str(error)
        raise typer.ClickException(detail) from error
    typer.echo(
        f"Generated and validated {len(execution.job.units)} units "
        f"in {output.resolve()} (job_id={execution.job.job_id})"
    )


def _validate_endpoint_dependencies(
    project_spec: ProjectSpec,
    module_specs: list[ModuleSpec],
) -> None:
    """Compatibility wrapper retained for callers of the former CLI helper."""

    try:
        validate_endpoint_dependencies(project_spec, tuple(module_specs))
    except GenerationSpecificationError as error:
        raise typer.BadParameter(str(error)) from error


def _validate_database_placements(
    project_spec: ProjectSpec,
    module_specs: list[ModuleSpec],
) -> None:
    """Compatibility wrapper retained for callers of the former CLI helper."""

    try:
        validate_database_placements(project_spec, tuple(module_specs))
    except GenerationSpecificationError as error:
        raise typer.BadParameter(str(error)) from error
