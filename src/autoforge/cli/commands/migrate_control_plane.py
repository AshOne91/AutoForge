import asyncio
import os
from pathlib import Path
from typing import Annotated

import typer

from autoforge.core.migration import discover_migrations

app = typer.Typer()


async def _run_migrations(
    *, database_url: str, migration_directory: Path
) -> tuple[int, ...]:
    try:
        from asyncpg import PostgresError
        from sqlalchemy.exc import SQLAlchemyError
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    except ImportError as error:
        raise RuntimeError(
            "Control Plane migration requires the AutoForge 'server' dependencies"
        ) from error

    from autoforge.infrastructure.migration import PostgreSQLMigrationExecutor

    engine = create_async_engine(database_url)
    try:
        executor = PostgreSQLMigrationExecutor(
            async_sessionmaker(engine, expire_on_commit=False)
        )
        applied = await executor.apply(discover_migrations(migration_directory))
        return tuple(record.version for record in applied)
    except (PostgresError, SQLAlchemyError) as error:
        raise RuntimeError(
            f"Control Plane migration failed: {type(error).__name__}"
        ) from error
    finally:
        await engine.dispose()


@app.callback(invoke_without_command=True)
def migrate_control_plane(
    migration_directory: Annotated[
        Path,
        typer.Option(exists=True, file_okay=False, readable=True),
    ] = Path("deploy/postgresql/init"),
    database_url_environment: Annotated[
        str,
        typer.Option(help="Environment variable containing the PostgreSQL URL."),
    ] = "AUTOFORGE_DATABASE_URL",
) -> None:
    """Apply Control Plane SQL through the explicit provider migration boundary."""

    database_url = os.environ.get(database_url_environment)
    if database_url is None or not database_url.strip():
        raise typer.BadParameter(
            f"environment variable {database_url_environment!r} needs a PostgreSQL URL.",
            param_hint="--database-url-environment",
        )
    try:
        applied_versions = asyncio.run(
            _run_migrations(
                database_url=database_url,
                migration_directory=migration_directory,
            )
        )
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error
    for version in applied_versions:
        typer.echo(version)
