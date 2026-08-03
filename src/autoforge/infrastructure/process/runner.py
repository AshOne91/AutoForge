import asyncio
import os
from collections.abc import Mapping
from pathlib import Path
from time import monotonic

from autoforge.services.validation.models import ProcessResult


class AsyncioProcessRunner:
    """Shell을 사용하지 않고 외부 프로세스를 비동기로 실행한다."""

    async def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float,
        environment: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        if not command:
            raise ValueError("실행 명령은 비어 있을 수 없습니다.")
        if timeout_seconds <= 0:
            raise ValueError("Timeout은 0보다 커야 합니다.")

        working_directory = cwd.resolve()
        if not working_directory.is_dir():
            raise ValueError(f"실행 디렉터리를 찾을 수 없습니다: {working_directory}")

        started_at = monotonic()
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_directory,
                env=_merged_environment(environment),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as error:
            return ProcessResult(
                command=command,
                exit_code=None,
                stdout="",
                stderr="",
                timed_out=False,
                duration_seconds=monotonic() - started_at,
                error=str(error),
            )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            process.kill()
            stdout, stderr = await process.communicate()
            return ProcessResult(
                command=command,
                exit_code=process.returncode,
                stdout=self._decode(stdout),
                stderr=self._decode(stderr),
                timed_out=True,
                duration_seconds=monotonic() - started_at,
            )

        return ProcessResult(
            command=command,
            exit_code=process.returncode,
            stdout=self._decode(stdout),
            stderr=self._decode(stderr),
            timed_out=False,
            duration_seconds=monotonic() - started_at,
        )

    @staticmethod
    def _decode(output: bytes) -> str:
        return output.decode("utf-8", errors="replace")


def _merged_environment(overrides: Mapping[str, str] | None) -> dict[str, str] | None:
    if overrides is None:
        return None
    environment = os.environ.copy()
    environment.update(overrides)
    return environment
