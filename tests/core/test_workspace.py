from pathlib import Path

import pytest

from autoforge.core.generation import (
    FileOwnership,
    PlannedAction,
    PlannedFile,
    content_hash,
)
from autoforge.core.workspace import Workspace, validate_workspace_relative_path


def test_workspace_resolves_relative_path_inside_root(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)

    resolved = workspace.resolve("src/game_server/main.py")

    assert resolved == tmp_path / "src" / "game_server" / "main.py"
    assert workspace.contains(resolved)


def test_workspace_normalizes_root(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "missing" / "..")

    assert workspace.root == tmp_path.resolve()


@pytest.mark.parametrize(
    "relative_path",
    [
        "/absolute/file.py",
        "C:/absolute/file.py",
        "../outside.py",
        "src/../../outside.py",
        r"src\game_server\main.py",
        "",
    ],
)
def test_workspace_rejects_unsafe_relative_paths(relative_path: str) -> None:
    with pytest.raises(ValueError):
        validate_workspace_relative_path(relative_path)


def test_workspace_contains_rejects_external_path(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "workspace")

    assert not workspace.contains(tmp_path / "outside.py")


def test_generation_model_uses_workspace_path_validation() -> None:
    hash_value = content_hash("content")

    with pytest.raises(ValueError, match="Workspace"):
        PlannedFile(
            relative_path="../outside.py",
            generator_id="autoforge.generator.fastapi",
            generator_version="0.1.0",
            ownership=FileOwnership.GENERATED,
            action=PlannedAction.CREATE,
            specification_hash=hash_value,
            expected_content_hash=hash_value,
            source="module:tutorial",
        )
