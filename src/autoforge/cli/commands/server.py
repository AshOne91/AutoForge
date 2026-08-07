import asyncio
import os
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from autoforge.composition import (
    ControlPlaneRuntimeSettings,
    create_control_plane_runtime,
)
from autoforge.core.config.loader import ConfigLoader

app = typer.Typer()


async def _run_server(
    runtime_settings: ControlPlaneRuntimeSettings,
    *,
    host: str,
    port: int,
) -> None:
    runtime = await create_control_plane_runtime(runtime_settings)
    server = uvicorn.Server(
        uvicorn.Config(runtime.app, host=host, port=port, log_level="info")
    )
    try:
        await server.serve()
    finally:
        await runtime.aclose()


@app.callback(invoke_without_command=True)
def server(
    config: Annotated[
        Path,
        typer.Option(exists=True, dir_okay=False, readable=True),
    ] = Path("autoforge.yaml"),
    source_root: Annotated[
        Path,
        typer.Option(exists=True, file_okay=False, readable=True),
    ] = Path("."),
    output_root: Annotated[Path | None, typer.Option(file_okay=False)] = None,
    database_url_environment: Annotated[
        str,
        typer.Option(help="Environment variable containing the PostgreSQL URL."),
    ] = "AUTOFORGE_DATABASE_URL",
    api_token_environment: Annotated[
        str,
        typer.Option(help="Environment variable containing the API bearer token."),
    ] = "AUTOFORGE_CONTROL_PLANE_TOKEN",
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option(min=1, max=65535)] = 8000,
    max_request_bytes: Annotated[int, typer.Option(min=1)] = 4096,
) -> None:
    """인증된 GenerationJob 제출 API를 별도 Worker와 독립적으로 실행한다."""

    database_url = os.environ.get(database_url_environment)
    api_token = os.environ.get(api_token_environment)
    if database_url is None or not database_url.strip():
        raise typer.BadParameter(
            f"환경 변수 {database_url_environment!r}에 PostgreSQL URL이 필요합니다.",
            param_hint="--database-url-environment",
        )
    if api_token is None or not api_token:
        raise typer.BadParameter(
            f"환경 변수 {api_token_environment!r}에 API bearer token이 필요합니다.",
            param_hint="--api-token-environment",
        )

    try:
        settings = ConfigLoader.load(config)
        asyncio.run(
            _run_server(
                ControlPlaneRuntimeSettings(
                    database_url=database_url,
                    api_token=api_token,
                    source_root=source_root,
                    output_root=output_root or Path(settings.workspace.output),
                    max_request_bytes=max_request_bytes,
                ),
                host=host,
                port=port,
            )
        )
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
