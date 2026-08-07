import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from autoforge.application.generation import GenerationWorkerLoopResult
from autoforge.cli.app import app
from autoforge.cli.commands import worker as worker_command
from autoforge.composition import GenerationWorkerRuntimeSettings

runner = CliRunner()


def _write_config(path: Path, output: Path) -> None:
    path.write_text(
        "\n".join(
            (
                "project:",
                "  name: AutoForge",
                '  version: "0.1.0"',
                "workspace:",
                f'  output: "{output.as_posix()}"',
                "logging:",
                "  level: INFO",
                "plugins:",
                "  enabled: []",
            )
        ),
        encoding="utf-8",
    )


def test_worker_requires_database_url_environment(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config = tmp_path / "autoforge.yaml"
    _write_config(config, tmp_path / "output")
    monkeypatch.delenv("AUTOFORGE_DATABASE_URL", raising=False)

    result = runner.invoke(
        app,
        ["worker", "--worker-id", "worker-a", "--config", str(config)],
    )

    assert result.exit_code == 2
    assert "AUTOFORGE_DATABASE_URL" in result.output
    assert "Traceback" not in result.output


def test_worker_uses_environment_and_validated_project_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config = tmp_path / "autoforge.yaml"
    output = tmp_path / "output"
    _write_config(config, output)
    captured: dict[str, object] = {}

    async def run_worker(
        runtime_settings: GenerationWorkerRuntimeSettings,
        git_config: object,
    ) -> GenerationWorkerLoopResult:
        captured["settings"] = runtime_settings
        captured["git_config"] = git_config
        return GenerationWorkerLoopResult(2, 0, 1, False)

    monkeypatch.setattr(worker_command, "_run_worker", run_worker)

    result = runner.invoke(
        app,
        ["worker", "--config", str(config), "--source-root", str(tmp_path)],
        env={
            "AUTOFORGE_WORKER_ID": "worker-from-environment",
            "AUTOFORGE_DATABASE_URL": "postgresql+asyncpg://user:secret@db/autoforge",
        },
    )

    assert result.exit_code == 0
    runtime_settings = captured["settings"]
    assert isinstance(runtime_settings, GenerationWorkerRuntimeSettings)
    assert runtime_settings.worker.worker_id == "worker-from-environment"
    assert runtime_settings.worker.output_root == output
    assert runtime_settings.isolated_workspace_root == (
        output / ".autoforge" / "workspaces"
    )
    assert "secret" not in result.output
    assert "completed=2" in result.output
    assert "recovered=1" in result.output


def test_run_worker_installs_shutdown_handlers(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    events: list[str] = []

    class RecordingRuntime:
        async def run(
            self,
            stop_event: asyncio.Event,
        ) -> GenerationWorkerLoopResult:
            events.append("run")
            assert not stop_event.is_set()
            return GenerationWorkerLoopResult(0, 0, 0, False)

    async def create_runtime(*args: object, **kwargs: object) -> RecordingRuntime:
        del args, kwargs
        events.append("create")
        return RecordingRuntime()

    @contextmanager
    def signal_handlers(stop_event: asyncio.Event) -> Iterator[None]:
        assert not stop_event.is_set()
        events.append("signals-enter")
        try:
            yield
        finally:
            events.append("signals-exit")

    monkeypatch.setattr(
        worker_command,
        "create_generation_worker_runtime",
        create_runtime,
    )
    monkeypatch.setattr(
        worker_command,
        "shutdown_signal_handlers",
        signal_handlers,
    )
    settings = GenerationWorkerRuntimeSettings(
        database_url="postgresql+asyncpg://user:secret@db/autoforge",
        worker=worker_command.GenerationWorkerSettings(
            worker_id="worker-a",
            source_root=tmp_path,
            output_root=tmp_path / "output",
        ),
        isolated_workspace_root=tmp_path / "workspaces",
    )

    asyncio.run(_run_worker(settings))

    assert events == ["create", "signals-enter", "run", "signals-exit"]


async def _run_worker(settings: GenerationWorkerRuntimeSettings) -> None:
    await worker_command._run_worker(
        settings,
        worker_command.GitAutomationConfig(),
    )
