import asyncio
import os
from pathlib import Path
from typing import Annotated

import typer

from autoforge.application.generation import (
    GenerationWorkerLoopResult,
    GenerationWorkerSettings,
)
from autoforge.composition import (
    GenerationWorkerRuntimeSettings,
    create_generation_worker_runtime,
)
from autoforge.core.config import GitAutomationConfig
from autoforge.core.config.loader import ConfigLoader
from autoforge.infrastructure.process import shutdown_signal_handlers

app = typer.Typer()


async def _run_worker(
    runtime_settings: GenerationWorkerRuntimeSettings,
    git_config: GitAutomationConfig,
) -> GenerationWorkerLoopResult:
    runtime = await create_generation_worker_runtime(
        runtime_settings,
        git_config=git_config,
    )
    stop_event = asyncio.Event()
    with shutdown_signal_handlers(stop_event):
        return await runtime.run(stop_event)


@app.callback(invoke_without_command=True)
def worker(
    worker_id: Annotated[
        str,
        typer.Option(
            envvar="AUTOFORGE_WORKER_ID",
            help="Unique worker identity; may also use AUTOFORGE_WORKER_ID.",
        ),
    ],
    config: Annotated[
        Path,
        typer.Option(exists=True, dir_okay=False, readable=True),
    ] = Path("autoforge.yaml"),
    source_root: Annotated[
        Path,
        typer.Option(exists=True, file_okay=False, readable=True),
    ] = Path("."),
    output_root: Annotated[Path | None, typer.Option(file_okay=False)] = None,
    isolated_workspace_root: Annotated[
        Path | None,
        typer.Option(file_okay=False),
    ] = None,
    database_url_environment: Annotated[
        str,
        typer.Option(help="Environment variable containing the PostgreSQL URL."),
    ] = "AUTOFORGE_DATABASE_URL",
    preserve_failed_workspace: Annotated[bool, typer.Option()] = False,
    validation_timeout_seconds: Annotated[float, typer.Option(min=0.001)] = 30.0,
) -> None:
    """PostgreSQL 작업을 가져와 생성 Pipeline을 지속 실행한다."""

    database_url = os.environ.get(database_url_environment)
    if database_url is None or not database_url.strip():
        raise typer.BadParameter(
            f"환경 변수 {database_url_environment!r}에 PostgreSQL URL이 필요합니다.",
            param_hint="--database-url-environment",
        )

    try:
        settings = ConfigLoader.load(config)
        resolved_output_root = output_root or Path(settings.workspace.output)
        resolved_workspace_root = isolated_workspace_root or (
            resolved_output_root / ".autoforge" / "workspaces"
        )
        result = asyncio.run(
            _run_worker(
                GenerationWorkerRuntimeSettings(
                    database_url=database_url,
                    worker=GenerationWorkerSettings(
                        worker_id=worker_id,
                        source_root=source_root,
                        output_root=resolved_output_root,
                    ),
                    isolated_workspace_root=resolved_workspace_root,
                    preserve_failed_workspace=preserve_failed_workspace,
                    validation_timeout_seconds=validation_timeout_seconds,
                ),
                settings.git_automation,
            )
        )
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error

    typer.echo(
        "Worker stopped "
        f"(completed={result.completed_jobs}, "
        f"failed={result.failed_attempts}, "
        f"recovered={result.recovered_jobs}, "
        f"shutdown_timed_out={result.shutdown_timed_out})"
    )
