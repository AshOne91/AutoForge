import typer

from autoforge.cli.commands.generate import app as generate_app
from autoforge.cli.commands.plugin import app as plugin_app
from autoforge.cli.commands.version import app as version_app
from autoforge.cli.commands.worker import app as worker_app

app = typer.Typer(
    help="AutoForge Development Automation Platform",
    no_args_is_help=True,
)

app.add_typer(version_app, name="version")
app.add_typer(plugin_app, name="plugin")
app.add_typer(generate_app, name="generate")
app.add_typer(worker_app, name="worker")
