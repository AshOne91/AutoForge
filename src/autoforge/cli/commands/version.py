import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def version():
    """
    Show AutoForge Version
    """
    typer.echo("AutoForge v0.1.0")