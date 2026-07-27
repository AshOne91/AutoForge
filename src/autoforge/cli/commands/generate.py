import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def generate():
    """Code generation"""
    typer.echo("Generate command")