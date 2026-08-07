import asyncio
from pathlib import Path

from autoforge.application.generation import (
    GenerationWorkerLoopResult,
    GenerationWorkerSettings,
)
from autoforge.composition import (
    GenerationWorkerRuntime,
    GenerationWorkerRuntimeSettings,
    create_generation_worker_runtime,
)
from autoforge.core.config import GitAutomationConfig


def _settings(tmp_path: Path) -> GenerationWorkerRuntimeSettings:
    return GenerationWorkerRuntimeSettings(
        database_url=(
            "postgresql+asyncpg://autoforge:autoforge@localhost:5432/autoforge"
        ),
        worker=GenerationWorkerSettings(
            worker_id="worker-a",
            source_root=tmp_path,
            output_root=tmp_path / "output",
        ),
        isolated_workspace_root=tmp_path / "workspaces",
    )


def test_runtime_composes_without_git_automation(tmp_path: Path) -> None:
    async def scenario() -> None:
        runtime = await create_generation_worker_runtime(_settings(tmp_path))
        try:
            assert runtime.git_automation is None
        finally:
            await runtime.aclose()

    asyncio.run(scenario())


def test_runtime_injects_enabled_git_automation(tmp_path: Path) -> None:
    async def scenario() -> None:
        runtime = await create_generation_worker_runtime(
            _settings(tmp_path),
            git_config=GitAutomationConfig(
                enabled=True,
                secret_names={"github_token": "AUTOFORGE_GITHUB_TOKEN"},
            ),
        )
        try:
            assert runtime.git_automation is not None
        finally:
            await runtime.aclose()

    asyncio.run(scenario())


def test_runtime_closes_http_and_database_resources() -> None:
    class IdleWorker:
        async def run_once(self) -> None:
            return None

    class RecordingLoop:
        async def run(self, stop_event: asyncio.Event) -> GenerationWorkerLoopResult:
            stop_event.set()
            return GenerationWorkerLoopResult(
                completed_jobs=0,
                failed_attempts=0,
                recovered_jobs=0,
                shutdown_timed_out=False,
            )

    class RecordingEngine:
        def __init__(self) -> None:
            self.dispose_calls = 0

        async def dispose(self) -> None:
            self.dispose_calls += 1

    class RecordingGitAutomation:
        def __init__(self) -> None:
            self.close_calls = 0

        async def aclose(self) -> None:
            self.close_calls += 1

    async def scenario() -> None:
        engine = RecordingEngine()
        git_automation = RecordingGitAutomation()
        runtime = GenerationWorkerRuntime(
            worker=IdleWorker(),
            worker_loop=RecordingLoop(),
            database_engine=engine,
            git_automation=git_automation,
        )
        result = await runtime.run(asyncio.Event())
        await runtime.aclose()

        assert result.completed_jobs == 0
        assert git_automation.close_calls == 1
        assert engine.dispose_calls == 1

    asyncio.run(scenario())
