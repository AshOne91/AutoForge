from pathlib import Path
from types import SimpleNamespace

from pytest import MonkeyPatch
from typer.testing import CliRunner

from autoforge.cli.app import app
from autoforge.cli.commands import generate as generate_command

runner = CliRunner()


def test_generate_uses_requested_validation_python(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    project = tmp_path / "autoforge.yaml"
    specifications = tmp_path / "specifications"
    validation_python = tmp_path / "python.exe"
    project.touch()
    specifications.mkdir()
    validation_python.touch()
    captured: dict[str, object] = {}

    class RecordingValidator:
        def __init__(self, _runner: object, **kwargs: object) -> None:
            captured.update(kwargs)

    class SuccessfulPipeline:
        async def run(self, _request: object) -> SimpleNamespace:
            return SimpleNamespace(job=SimpleNamespace(units=("unit",), job_id="job"))

    monkeypatch.setattr(generate_command, "ProjectValidator", RecordingValidator)
    monkeypatch.setattr(
        generate_command,
        "GenerationJobPipeline",
        lambda **_kwargs: SuccessfulPipeline(),
    )

    result = runner.invoke(
        app,
        [
            "generate",
            "--project",
            str(project),
            "--specifications",
            str(specifications),
            "--output",
            str(tmp_path),
            "--validation-python",
            str(validation_python),
        ],
    )

    assert result.exit_code == 0
    assert captured == {"python_executable": str(validation_python)}
