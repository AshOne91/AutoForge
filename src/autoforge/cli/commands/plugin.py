import typer

app = typer.Typer()


@app.callback(invoke_without_command=True)
def plugin() -> None:
    """Plugin Framework의 현재 구현 상태를 알린다."""
    typer.echo(
        "plugin 명령은 PluginLoader 구현 이후 제공됩니다.",
        err=True,
    )
    raise typer.Exit(code=1)
