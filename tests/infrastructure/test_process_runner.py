import sys
from pathlib import Path

import pytest

from autoforge.infrastructure.process import AsyncioProcessRunner


@pytest.mark.anyio
async def test_runner_captures_success_output(tmp_path: Path) -> None:
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", "print('out'); raise SystemExit(0)"),
        cwd=tmp_path,
        timeout_seconds=5,
    )

    assert result.succeeded
    assert result.exit_code == 0
    assert result.stdout.strip() == "out"
    assert result.stderr == ""
    assert not result.timed_out
    assert result.duration_seconds >= 0


@pytest.mark.anyio
async def test_runner_captures_failure_output(tmp_path: Path) -> None:
    result = await AsyncioProcessRunner().run(
        (
            sys.executable,
            "-c",
            "import sys; print('error', file=sys.stderr); raise SystemExit(3)",
        ),
        cwd=tmp_path,
        timeout_seconds=5,
    )

    assert not result.succeeded
    assert result.exit_code == 3
    assert result.stderr.strip() == "error"


@pytest.mark.anyio
async def test_runner_terminates_timed_out_process(tmp_path: Path) -> None:
    result = await AsyncioProcessRunner().run(
        (sys.executable, "-c", "import time; time.sleep(10)"),
        cwd=tmp_path,
        timeout_seconds=0.05,
    )

    assert not result.succeeded
    assert result.timed_out


@pytest.mark.anyio
async def test_runner_reports_missing_executable(tmp_path: Path) -> None:
    result = await AsyncioProcessRunner().run(
        ("autoforge-command-that-does-not-exist",),
        cwd=tmp_path,
        timeout_seconds=5,
    )

    assert not result.succeeded
    assert result.exit_code is None
    assert result.error


@pytest.mark.anyio
async def test_runner_rejects_invalid_working_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="실행 디렉터리"):
        await AsyncioProcessRunner().run(
            (sys.executable, "--version"),
            cwd=tmp_path / "missing",
            timeout_seconds=5,
        )
