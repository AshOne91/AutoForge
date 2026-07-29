import typer

from autoforge import __version__

app = typer.Typer()


@app.callback(invoke_without_command=True)
def version() -> None:
    typer.echo(f"AutoForge v{__version__}")
