from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Protocol

from autoforge.application.generation import (
    GenerationJobPipeline,
    GenerationPlanningService,
    GenerationWorker,
    GenerationWorkerLoop,
    GenerationWorkerLoopResult,
    GenerationWorkerLoopSettings,
    GenerationWorkerSettings,
)
from autoforge.application.generation.worker import GenerationWorkerProtocol
from autoforge.composition.git_automation import (
    GitAutomationComponents,
    create_git_automation_components,
)
from autoforge.core.config import GitAutomationConfig
from autoforge.core.event import EventBus
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.infrastructure.workspace import IsolatedWorkspaceManager
from autoforge.services.validation import ProjectValidator


class DatabaseEngine(Protocol):
    async def dispose(self) -> None: ...


class AsyncCloseable(Protocol):
    async def aclose(self) -> None: ...


class WorkerLoop(Protocol):
    async def run(
        self, stop_event: asyncio.Event
    ) -> GenerationWorkerLoopResult: ...


@dataclass(frozen=True, slots=True)
class GenerationWorkerRuntimeSettings:
    database_url: str = field(repr=False)
    worker: GenerationWorkerSettings
    isolated_workspace_root: Path
    loop: GenerationWorkerLoopSettings = field(
        default_factory=GenerationWorkerLoopSettings
    )
    preserve_failed_workspace: bool = False
    validation_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.database_url.strip():
            raise ValueError("database_url must not be empty")
        if self.validation_timeout_seconds <= 0:
            raise ValueError("validation_timeout_seconds must be positive")


@dataclass(slots=True)
class GenerationWorkerRuntime:
    """Own the worker loop and every external resource created for it."""

    worker: GenerationWorkerProtocol
    worker_loop: WorkerLoop
    database_engine: DatabaseEngine
    git_automation: AsyncCloseable | None = None
    _closed: bool = field(default=False, init=False, repr=False)

    async def run(
        self,
        stop_event: asyncio.Event,
    ) -> GenerationWorkerLoopResult:
        try:
            return await self.worker_loop.run(stop_event)
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self.git_automation is not None:
                await self.git_automation.aclose()
        finally:
            await self.database_engine.dispose()


async def create_generation_worker_runtime(
    settings: GenerationWorkerRuntimeSettings,
    *,
    git_config: GitAutomationConfig | None = None,
    process_runner: AsyncioProcessRunner | None = None,
) -> GenerationWorkerRuntime:
    """Compose the persistent generation worker without starting its loop."""

    try:
        sqlalchemy_asyncio = import_module("sqlalchemy.ext.asyncio")
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Generation worker requires the AutoForge 'server' dependencies"
        ) from error

    from autoforge.infrastructure.job.postgresql import PostgreSQLJobStore

    engine = sqlalchemy_asyncio.create_async_engine(settings.database_url)
    git_automation: GitAutomationComponents | None = None
    try:
        sessions = sqlalchemy_asyncio.async_sessionmaker(
            engine, expire_on_commit=False
        )
        job_store = PostgreSQLJobStore(sessions)
        event_bus = EventBus()
        runner = process_runner or AsyncioProcessRunner()
        pipeline = GenerationJobPipeline(
            job_store=job_store,
            event_bus=event_bus,
            validator=ProjectValidator(
                runner,
                timeout_seconds=settings.validation_timeout_seconds,
            ),
        )
        git_automation = create_git_automation_components(
            git_config or GitAutomationConfig(),
            process_runner=runner,
        )

        if git_automation is None:
            worker = GenerationWorker(
                settings=settings.worker,
                job_store=job_store,
                pipeline=pipeline,
                event_bus=event_bus,
            )
        else:
            worker = GenerationWorker(
                settings=settings.worker,
                job_store=job_store,
                pipeline=pipeline,
                event_bus=event_bus,
                git_provider=git_automation.git_provider,
                workspace_manager=IsolatedWorkspaceManager(
                    settings.isolated_workspace_root,
                    preserve_on_error=settings.preserve_failed_workspace,
                ),
                planning_service=GenerationPlanningService(
                    job_store=job_store,
                    event_bus=event_bus,
                ),
                git_commit_settings=git_automation.git_commit_settings,
                git_push_settings=git_automation.git_push_settings,
                pull_request_provider=git_automation.pull_request_provider,
                pull_request_settings=git_automation.pull_request_settings,
            )
        return GenerationWorkerRuntime(
            worker=worker,
            worker_loop=GenerationWorkerLoop(
                worker=worker,
                job_store=job_store,
                settings=settings.loop,
            ),
            database_engine=engine,
            git_automation=git_automation,
        )
    except BaseException:
        try:
            if git_automation is not None:
                await git_automation.aclose()
        finally:
            await engine.dispose()
        raise
