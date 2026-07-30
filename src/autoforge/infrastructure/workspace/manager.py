import asyncio
import re
import shutil
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Final

from autoforge.core.workspace import Workspace

WORKSPACE_NAME_PATTERN: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
MAX_WORKSPACE_NAME_LENGTH: Final = 64


class IsolatedWorkspaceManager:
    """작업별 임시 Workspace를 만들고 정책에 따라 정리한다."""

    def __init__(
        self,
        base_directory: Path,
        *,
        preserve_on_error: bool = False,
    ) -> None:
        self._base_directory = base_directory.resolve()
        self._preserve_on_error = preserve_on_error

    @asynccontextmanager
    async def create(self, workspace_name: str) -> AsyncIterator[Workspace]:
        validated_name = self._validate_name(workspace_name)
        self._prepare_base_directory()
        root = Path(
            tempfile.mkdtemp(
                prefix=f"{validated_name}-",
                dir=self._base_directory,
            )
        ).resolve()
        workspace = Workspace(root)
        failed = False
        try:
            yield workspace
        except BaseException:
            failed = True
            raise
        finally:
            if not (failed and self._preserve_on_error):
                self._validate_cleanup_target(root)
                await asyncio.to_thread(shutil.rmtree, root)

    def _prepare_base_directory(self) -> None:
        if self._base_directory.exists() and not self._base_directory.is_dir():
            raise ValueError(
                f"Workspace 기본 경로가 디렉터리가 아닙니다: {self._base_directory}"
            )
        self._base_directory.mkdir(parents=True, exist_ok=True)

    def _validate_cleanup_target(self, root: Path) -> None:
        try:
            relative_path = root.resolve().relative_to(self._base_directory)
        except ValueError as error:
            raise RuntimeError(
                "정리 대상이 Workspace 기본 경로 밖을 가리킵니다."
            ) from error
        if len(relative_path.parts) != 1:
            raise RuntimeError("정리 대상은 격리 Workspace 루트여야 합니다.")

    @staticmethod
    def _validate_name(workspace_name: str) -> str:
        if (
            not workspace_name
            or len(workspace_name) > MAX_WORKSPACE_NAME_LENGTH
            or WORKSPACE_NAME_PATTERN.fullmatch(workspace_name) is None
            or workspace_name in {".", ".."}
        ):
            raise ValueError(
                "Workspace 이름은 영문자 또는 숫자로 시작하는 64자 이하의 "
                "영문자, 숫자, 점, 밑줄과 하이픈이어야 합니다."
            )
        return workspace_name
