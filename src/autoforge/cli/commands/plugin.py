import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def plugin():
    typer.echo("Plugin command")