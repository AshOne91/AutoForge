import asyncio
from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from autoforge.cli.app import app
from autoforge.cli.commands import server as server_command
from autoforge.composition import ControlPlaneRuntimeSettings

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


def test_server_requires_secret_environment_values(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config = tmp_path / "autoforge.yaml"
    _write_config(config, tmp_path / "output")
    monkeypatch.delenv("AUTOFORGE_DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTOFORGE_CONTROL_PLANE_TOKEN", raising=False)

    result = runner.invoke(app, ["server", "--config", str(config)])

    assert result.exit_code == 2
    assert "AUTOFORGE_DATABASE_URL" in result.output
    assert "Traceback" not in result.output


def test_server_uses_environment_and_validated_project_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config = tmp_path / "autoforge.yaml"
    output = tmp_path / "output"
    _write_config(config, output)
    captured: dict[str, object] = {}

    async def run_server(
        runtime_settings: ControlPlaneRuntimeSettings,
        *,
        host: str,
        port: int,
    ) -> None:
        captured["settings"] = runtime_settings
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setattr(server_command, "_run_server", run_server)

    result = runner.invoke(
        app,
        [
            "server",
            "--config",
            str(config),
            "--source-root",
            str(tmp_path),
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
        ],
        env={
            "AUTOFORGE_DATABASE_URL": "postgresql+asyncpg://user:secret@db/autoforge",
            "AUTOFORGE_CONTROL_PLANE_TOKEN": "server-secret",
        },
    )

    assert result.exit_code == 0
    runtime_settings = captured["settings"]
    assert isinstance(runtime_settings, ControlPlaneRuntimeSettings)
    assert runtime_settings.output_root == output
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9000
    assert "secret" not in result.output


def test_run_server_closes_runtime_after_uvicorn_stops(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    events: list[str] = []

    class RecordingRuntime:
        app = object()

        async def aclose(self) -> None:
            events.append("close")

    class RecordingServer:
        def __init__(self, config: object) -> None:
            del config
            events.append("server-create")

        async def serve(self) -> None:
            events.append("serve")

    async def create_runtime(*args: object, **kwargs: object) -> RecordingRuntime:
        del args, kwargs
        events.append("runtime-create")
        return RecordingRuntime()

    monkeypatch.setattr(
        server_command,
        "create_control_plane_runtime",
        create_runtime,
    )
    monkeypatch.setattr(server_command.uvicorn, "Server", RecordingServer)
    settings = ControlPlaneRuntimeSettings(
        database_url="postgresql+asyncpg://user:secret@db/autoforge",
        api_token="server-secret",
        source_root=tmp_path,
        output_root=tmp_path / "output",
    )

    asyncio.run(server_command._run_server(settings, host="127.0.0.1", port=8000))

    assert events == ["runtime-create", "server-create", "serve", "close"]
