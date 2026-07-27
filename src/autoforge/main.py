import typer

app = typer.Typer(
    help="AutoForge - Development Automation Platform",
    no_args_is_help=True,
)


@app.command()
def version():
    """Show AutoForge version"""
    typer.echo("AutoForge v0.1.0")


@app.command()
def hello():
    """Test command"""
    typer.echo("Hello AutoForge!")


if __name__ == "__main__":
    app()