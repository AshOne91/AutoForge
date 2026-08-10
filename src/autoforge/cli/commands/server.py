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
from autoforge.infrastructure.http import GitHubWebhookSettings
from autoforge.infrastructure.observability import configure_logging

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
    github_webhook_secret_environment: Annotated[
        str | None,
        typer.Option(help="Environment variable containing the GitHub webhook secret."),
    ] = None,
    github_webhook_repository: Annotated[
        str | None,
        typer.Option(help="Allowed GitHub repository in owner/name form."),
    ] = None,
    github_webhook_ref: Annotated[str, typer.Option()] = "refs/heads/main",
    github_webhook_project_path: Annotated[str, typer.Option()] = "autoforge.yaml",
    github_webhook_specifications_path: Annotated[
        str, typer.Option()
    ] = "specifications",
    github_webhook_output_path: Annotated[str, typer.Option()] = ".",
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

    github_webhook = None
    if github_webhook_secret_environment is not None:
        webhook_secret = os.environ.get(github_webhook_secret_environment)
        if webhook_secret is None or not webhook_secret:
            raise typer.BadParameter(
                f"environment variable {github_webhook_secret_environment!r} needs a GitHub webhook secret.",
                param_hint="--github-webhook-secret-environment",
            )
        if github_webhook_repository is None:
            raise typer.BadParameter(
                "a repository is required when a GitHub webhook secret is configured.",
                param_hint="--github-webhook-repository",
            )
        try:
            github_webhook = GitHubWebhookSettings(
                secret=webhook_secret,
                allowed_repositories=frozenset({github_webhook_repository}),
                allowed_refs=frozenset({github_webhook_ref}),
                project_path=github_webhook_project_path,
                specifications_path=github_webhook_specifications_path,
                output_path=github_webhook_output_path,
            )
        except ValueError as error:
            raise typer.BadParameter(
                str(error),
                param_hint="--github-webhook-repository",
            ) from error
    elif github_webhook_repository is not None:
        raise typer.BadParameter(
            "a GitHub webhook secret environment is required when a repository is configured.",
            param_hint="--github-webhook-secret-environment",
        )

    try:
        settings = ConfigLoader.load(config)
        configure_logging(settings.logging)
        if github_webhook is not None and not settings.git_automation.enabled:
            raise ValueError("GitHub webhook requires enabled git_automation")
        asyncio.run(
            _run_server(
                ControlPlaneRuntimeSettings(
                    database_url=database_url,
                    api_token=api_token,
                    source_root=source_root,
                    output_root=output_root or Path(settings.workspace.output),
                    max_request_bytes=max_request_bytes,
                    github_webhook=github_webhook,
                ),
                host=host,
                port=port,
            )
        )
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
