import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoforge.composition import (
    ControlPlaneRuntime,
    ControlPlaneRuntimeSettings,
    create_control_plane_runtime,
)


def _settings(tmp_path: Path) -> ControlPlaneRuntimeSettings:
    return ControlPlaneRuntimeSettings(
        database_url="postgresql+asyncpg://autoforge:secret@localhost/autoforge",
        api_token="control-plane-token",
        source_root=tmp_path,
        output_root=tmp_path / "output",
    )


def test_control_plane_runtime_composes_postgresql_submission_api(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        runtime = await create_control_plane_runtime(_settings(tmp_path))
        try:
            assert runtime.app.title == "AutoForge Control Plane"
        finally:
            await runtime.aclose()

    asyncio.run(scenario())


def test_control_plane_runtime_closes_database_once() -> None:
    class RecordingEngine:
        def __init__(self) -> None:
            self.dispose_calls = 0

        async def dispose(self) -> None:
            self.dispose_calls += 1

    async def scenario() -> None:
        engine = RecordingEngine()
        runtime = ControlPlaneRuntime(app=FastAPI(), database_engine=engine)
        await runtime.aclose()
        await runtime.aclose()

        assert engine.dispose_calls == 1

    asyncio.run(scenario())


def test_control_plane_lifespan_closes_runtime(tmp_path: Path) -> None:
    async def scenario() -> ControlPlaneRuntime:
        return await create_control_plane_runtime(_settings(tmp_path))

    runtime = asyncio.run(scenario())
    with TestClient(runtime.app):
        pass

    assert runtime._closed
