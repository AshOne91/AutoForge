from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI

from autoforge.application.generation import GenerationSubmissionService
from autoforge.core.event import EventBus
from autoforge.infrastructure.http import (
    ControlPlaneHTTPSettings,
    create_control_plane_app,
)


class DatabaseEngine(Protocol):
    async def dispose(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ControlPlaneRuntimeSettings:
    database_url: str = field(repr=False)
    api_token: str = field(repr=False)
    source_root: Path
    output_root: Path
    max_request_bytes: int = 4096

    def __post_init__(self) -> None:
        if not self.database_url.strip():
            raise ValueError("database_url must not be empty")
        if not self.api_token:
            raise ValueError("api_token must not be empty")
        if self.max_request_bytes < 1:
            raise ValueError("max_request_bytes must be positive")


@dataclass(slots=True)
class ControlPlaneRuntime:
    """Own the Control Plane app and its PostgreSQL engine."""

    app: FastAPI
    database_engine: DatabaseEngine
    _closed: bool = field(default=False, init=False, repr=False)

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self.database_engine.dispose()


async def create_control_plane_runtime(
    settings: ControlPlaneRuntimeSettings,
) -> ControlPlaneRuntime:
    """Compose the authenticated HTTP submission API without starting a worker."""

    try:
        sqlalchemy_asyncio = import_module("sqlalchemy.ext.asyncio")
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Control Plane requires the AutoForge 'server' dependencies"
        ) from error

    from autoforge.infrastructure.job.postgresql import PostgreSQLJobStore

    engine = sqlalchemy_asyncio.create_async_engine(settings.database_url)
    runtime: ControlPlaneRuntime | None = None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if runtime is not None:
                await runtime.aclose()

    try:
        sessions = sqlalchemy_asyncio.async_sessionmaker(
            engine, expire_on_commit=False
        )
        job_store = PostgreSQLJobStore(sessions)
        app = create_control_plane_app(
            service=GenerationSubmissionService(
                source_root=settings.source_root,
                output_root=settings.output_root,
                job_store=job_store,
                event_bus=EventBus(),
            ),
            settings=ControlPlaneHTTPSettings(
                api_token=settings.api_token,
                max_request_bytes=settings.max_request_bytes,
            ),
            lifespan=lifespan,
        )
        runtime = ControlPlaneRuntime(app=app, database_engine=engine)
        return runtime
    except BaseException:
        await engine.dispose()
        raise
