import typer

from autoforge.core.config import config

app = typer.Typer()


@app.callback(invoke_without_command=True)
def version():
    typer.echo(f"{config.project.name} v{config.project.version}")