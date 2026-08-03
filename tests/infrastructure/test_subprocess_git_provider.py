from pathlib import Path

import pytest

from autoforge.core.git import GitCheckoutPolicy, GitCheckoutRequest
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.git import SubprocessGitProvider
from autoforge.infrastructure.process import AsyncioProcessRunner


async def _git(cwd: Path, *arguments: str) -> str:
    result = await AsyncioProcessRunner().run(
        ("git", *arguments), cwd=cwd, timeout_seconds=10
    )
    assert result.succeeded, result.stderr or result.error
    return result.stdout.strip()


async def _create_repository(root: Path) -> tuple[Path, str]:
    repository = root / "sources" / "sample"
    repository.mkdir(parents=True)
    await _git(repository, "init")
    await _git(repository, "config", "user.name", "AutoForge Test")
    await _git(repository, "config", "user.email", "autoforge@example.invalid")
    (repository / "README.md").write_text("first\n", encoding="utf-8")
    await _git(repository, "add", "README.md")
    await _git(repository, "commit", "-m", "initial")
    commit_sha = await _git(repository, "rev-parse", "HEAD")
    return repository, commit_sha


@pytest.mark.anyio
async def test_provider_checks_out_exact_clean_detached_commit(
    tmp_path: Path,
) -> None:
    source, commit_sha = await _create_repository(tmp_path)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    provider = SubprocessGitProvider(
        policy=GitCheckoutPolicy(
            allowed_hosts=frozenset(),
            allowed_local_roots=(tmp_path / "sources",),
        )
    )

    result = await provider.checkout(
        GitCheckoutRequest(str(source), commit_sha),
        workspace=Workspace(workspace_root),
    )

    assert result.commit_sha == commit_sha.lower()
    assert result.repository_path == (workspace_root / "repository").resolve()
    assert (result.repository_path / "README.md").read_text(encoding="utf-8") == (
        "first\n"
    )
    assert await _git(result.repository_path, "rev-parse", "HEAD") == commit_sha
    assert await _git(result.repository_path, "status", "--porcelain") == ""
    assert await _git(source, "status", "--porcelain") == ""


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("repository_url", "revision", "message"),
    (
        ("https://token@github.com/example/repo.git", "main", "credentials"),
        ("https://evil.example/repo.git", "main", "host"),
        ("file:///outside/repo", "main", "https"),
        ("https://github.com/example/repo.git", "--upload-pack=evil", "revision"),
        ("https://github.com/example/repo.git", "main..evil", "revision"),
    ),
)
async def test_provider_rejects_unsafe_repository_or_revision(
    tmp_path: Path,
    repository_url: str,
    revision: str,
    message: str,
) -> None:
    provider = SubprocessGitProvider(
        policy=GitCheckoutPolicy(allowed_hosts=frozenset({"github.com"}))
    )

    with pytest.raises(ValueError, match=message):
        await provider.checkout(
            GitCheckoutRequest(repository_url, revision),
            workspace=Workspace(tmp_path),
        )


@pytest.mark.anyio
async def test_provider_rejects_local_path_and_destination_outside_policy(
    tmp_path: Path,
) -> None:
    source, commit_sha = await _create_repository(tmp_path)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    provider = SubprocessGitProvider(
        policy=GitCheckoutPolicy(
            allowed_hosts=frozenset(),
            allowed_local_roots=(tmp_path / "different-root",),
        )
    )

    with pytest.raises(ValueError, match="not allowed"):
        await provider.checkout(
            GitCheckoutRequest(str(source), commit_sha),
            workspace=Workspace(workspace_root),
        )

    allowed = SubprocessGitProvider(
        policy=GitCheckoutPolicy(
            allowed_hosts=frozenset(),
            allowed_local_roots=(tmp_path / "sources",),
        )
    )
    with pytest.raises(ValueError, match=r"\.\."):
        await allowed.checkout(
            GitCheckoutRequest(str(source), commit_sha, destination="../outside"),
            workspace=Workspace(workspace_root),
        )
