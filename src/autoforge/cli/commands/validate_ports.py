from pathlib import Path
from typing import Annotated

import typer

from autoforge.services.port_preflight import validate_port_override_files

app = typer.Typer()


@app.callback(invoke_without_command=True)
def validate_ports(
    env_files: Annotated[
        list[Path],
        typer.Option("--env-file", exists=True, file_okay=True, dir_okay=False),
    ],
) -> None:
    """Check published host-port overrides before starting Compose."""

    if not env_files:
        raise typer.BadParameter("provide at least one --env-file")
    try:
        ports = validate_port_override_files(tuple(env_files))
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"Validated {len(ports)} host-port override(s)")
