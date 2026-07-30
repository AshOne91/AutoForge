from pathlib import Path

import pytest

from autoforge.infrastructure.workspace import IsolatedWorkspaceManager


@pytest.mark.anyio
async def test_manager_creates_and_cleans_isolated_workspace(
    tmp_path: Path,
) -> None:
    base_directory = tmp_path / "workspaces"

    async with IsolatedWorkspaceManager(base_directory).create("job-001") as workspace:
        root = workspace.root
        assert root.is_dir()
        assert root.parent == base_directory
        assert root.name.startswith("job-001-")

    assert not root.exists()
    assert base_directory.is_dir()


@pytest.mark.anyio
async def test_manager_cleans_workspace_after_error(tmp_path: Path) -> None:
    manager = IsolatedWorkspaceManager(tmp_path / "workspaces")
    root: Path | None = None

    with pytest.raises(RuntimeError, match="generation failed"):
        async with manager.create("job-001") as workspace:
            root = workspace.root
            raise RuntimeError("generation failed")

    assert root is not None
    assert not root.exists()


@pytest.mark.anyio
async def test_manager_can_preserve_failed_workspace(tmp_path: Path) -> None:
    manager = IsolatedWorkspaceManager(
        tmp_path / "workspaces",
        preserve_on_error=True,
    )
    root: Path | None = None

    with pytest.raises(RuntimeError, match="generation failed"):
        async with manager.create("job-001") as workspace:
            root = workspace.root
            (root / "diagnostic.txt").write_text("failure", encoding="utf-8")
            raise RuntimeError("generation failed")

    assert root is not None
    assert (root / "diagnostic.txt").read_text(encoding="utf-8") == "failure"


@pytest.mark.anyio
async def test_manager_creates_different_roots_for_each_workspace(
    tmp_path: Path,
) -> None:
    manager = IsolatedWorkspaceManager(tmp_path / "workspaces")

    async with (
        manager.create("job-001") as first,
        manager.create("job-001") as second,
    ):
        assert first.root != second.root
        assert not first.contains(second.root)
        assert not second.contains(first.root)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "workspace_name",
    ["", ".", "..", "../outside", "nested/job", r"nested\job", "-job"],
)
async def test_manager_rejects_unsafe_workspace_name(
    tmp_path: Path,
    workspace_name: str,
) -> None:
    manager = IsolatedWorkspaceManager(tmp_path / "workspaces")

    with pytest.raises(ValueError, match="Workspace 이름"):
        async with manager.create(workspace_name):
            pass


@pytest.mark.anyio
async def test_manager_rejects_file_as_base_directory(tmp_path: Path) -> None:
    base_directory = tmp_path / "workspaces"
    base_directory.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ValueError, match="디렉터리가 아닙니다"):
        async with IsolatedWorkspaceManager(base_directory).create("job-001"):
            pass
