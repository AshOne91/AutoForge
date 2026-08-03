from collections.abc import Mapping
from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.git import (
    GitCheckoutPolicy,
    GitCheckoutRequest,
    GitCommitRequest,
    GitCredentialReference,
    GitPushRequest,
)
from autoforge.core.secret import SecretReference
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.git import GitProviderError, SubprocessGitProvider
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.infrastructure.secret import InMemorySecretProvider
from autoforge.services.validation import ProcessResult


class RecordingGitRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], Mapping[str, str] | None]] = []

    async def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float,
        environment: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        del cwd, timeout_seconds
        self.calls.append((command, environment))
        if "clone" in command:
            destination = Path(command[-1])
            destination.mkdir(parents=True)
            (destination / ".git").mkdir()
        stdout = "a" * 40 if "rev-parse" in command else ""
        return ProcessResult(
            command=command,
            exit_code=0,
            stdout=stdout,
            stderr="",
            timed_out=False,
            duration_seconds=0,
        )


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
async def test_https_checkout_keeps_resolved_secret_out_of_url_and_arguments(
    tmp_path: Path,
) -> None:
    token = "github-token-never-log"
    runner = RecordingGitRunner()
    provider = SubprocessGitProvider(
        policy=GitCheckoutPolicy(allowed_hosts=frozenset({"github.com"})),
        process_runner=runner,  # type: ignore[arg-type]
        secret_provider=InMemorySecretProvider(
            {"git/github/token": token}
        ),
    )

    await provider.checkout(
        GitCheckoutRequest(
            "https://github.com/example/repository.git",
            "main",
            credential=GitCredentialReference(
                username="x-access-token",
                password=SecretReference("git/github/token"),
            ),
        ),
        workspace=Workspace(tmp_path),
    )

    assert runner.calls
    assert all(token not in argument for command, _ in runner.calls for argument in command)
    clone_environment = runner.calls[0][1]
    assert clone_environment is not None
    assert clone_environment["AUTOFORGE_GIT_PASSWORD"] == token
    assert not Path(clone_environment["GIT_ASKPASS"]).exists()
    assert all(
        environment is None or "AUTOFORGE_GIT_PASSWORD" not in environment
        for _, environment in runner.calls[1:]
    )


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


@pytest.mark.anyio
async def test_provider_commits_only_allowlisted_validated_changes(
    tmp_path: Path,
) -> None:
    source, base_sha = await _create_repository(tmp_path)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace = Workspace(workspace_root)
    provider = SubprocessGitProvider(
        policy=GitCheckoutPolicy(
            allowed_hosts=frozenset(),
            allowed_local_roots=(tmp_path / "sources",),
        )
    )
    checkout = await provider.checkout(
        GitCheckoutRequest(str(source), base_sha), workspace=workspace
    )
    generated = checkout.repository_path / "generated" / "service.py"
    generated.parent.mkdir()
    generated.write_text("value = 1\n", encoding="utf-8")
    unexpected = checkout.repository_path / "unexpected.txt"
    unexpected.write_text("not generated\n", encoding="utf-8")
    request = GitCommitRequest(
        expected_base_sha=base_sha,
        branch_name="autoforge/job-1",
        message="chore: generate service",
        author_name="AutoForge",
        author_email="autoforge@example.invalid",
        allowed_paths=(PurePosixPath("generated/service.py"),),
    )

    with pytest.raises(GitProviderError, match="outside the allowlist"):
        await provider.commit_validated(request, workspace=workspace)

    assert await _git(checkout.repository_path, "branch", "--show-current") == ""
    unexpected.unlink()
    result = await provider.commit_validated(request, workspace=workspace)

    assert result.commit_created is True
    assert result.branch_name == "autoforge/job-1"
    assert result.changed_paths == (PurePosixPath("generated/service.py"),)
    assert result.commit_sha != base_sha
    assert await _git(checkout.repository_path, "branch", "--show-current") == (
        "autoforge/job-1"
    )
    assert await _git(
        checkout.repository_path, "show", "-s", "--format=%an <%ae>"
    ) == "AutoForge <autoforge@example.invalid>"
    assert await _git(checkout.repository_path, "status", "--porcelain") == ""
    assert await _git(source, "rev-parse", "HEAD") == base_sha
    assert not (source / "generated").exists()


@pytest.mark.anyio
async def test_provider_does_not_create_branch_or_commit_without_changes(
    tmp_path: Path,
) -> None:
    source, base_sha = await _create_repository(tmp_path)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace = Workspace(workspace_root)
    provider = SubprocessGitProvider(
        policy=GitCheckoutPolicy(
            allowed_hosts=frozenset(),
            allowed_local_roots=(tmp_path / "sources",),
        )
    )
    checkout = await provider.checkout(
        GitCheckoutRequest(str(source), base_sha), workspace=workspace
    )

    result = await provider.commit_validated(
        GitCommitRequest(
            expected_base_sha=base_sha,
            branch_name="autoforge/job-2",
            message="chore: generate service",
            author_name="AutoForge",
            author_email="autoforge@example.invalid",
            allowed_paths=(PurePosixPath("generated/service.py"),),
        ),
        workspace=workspace,
    )

    assert result.commit_created is False
    assert result.commit_sha == base_sha
    assert result.branch_name is None
    assert result.changed_paths == ()
    assert await _git(checkout.repository_path, "branch", "--show-current") == ""


@pytest.mark.anyio
async def test_provider_rejects_wrong_base_and_unsafe_branch_before_mutation(
    tmp_path: Path,
) -> None:
    source, base_sha = await _create_repository(tmp_path)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace = Workspace(workspace_root)
    provider = SubprocessGitProvider(
        policy=GitCheckoutPolicy(
            allowed_hosts=frozenset(),
            allowed_local_roots=(tmp_path / "sources",),
        )
    )
    checkout = await provider.checkout(
        GitCheckoutRequest(str(source), base_sha), workspace=workspace
    )
    generated = checkout.repository_path / "generated.py"
    generated.write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(GitProviderError, match="expected base"):
        await provider.commit_validated(
            GitCommitRequest(
                expected_base_sha="b" * 40,
                branch_name="autoforge/job-3",
                message="chore: generate service",
                author_name="AutoForge",
                author_email="autoforge@example.invalid",
                allowed_paths=(PurePosixPath("generated.py"),),
            ),
            workspace=workspace,
        )

    with pytest.raises(ValueError, match="branch"):
        await provider.commit_validated(
            GitCommitRequest(
                expected_base_sha=base_sha,
                branch_name="--upload-pack=evil",
                message="chore: generate service",
                author_name="AutoForge",
                author_email="autoforge@example.invalid",
                allowed_paths=(PurePosixPath("generated.py"),),
            ),
            workspace=workspace,
        )

    assert await _git(checkout.repository_path, "branch", "--show-current") == ""
    assert await _git(checkout.repository_path, "rev-parse", "HEAD") == base_sha
    assert await _git(checkout.repository_path, "status", "--porcelain") == (
        "?? generated.py"
    )


@pytest.mark.anyio
async def test_provider_pushes_validated_branch_non_force_and_is_idempotent(
    tmp_path: Path,
) -> None:
    source, base_sha = await _create_repository(tmp_path)
    remote = tmp_path / "remotes" / "generated.git"
    remote.parent.mkdir()
    remote.mkdir()
    await _git(remote, "init", "--bare")
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    workspace = Workspace(workspace_root)
    provider = SubprocessGitProvider(
        policy=GitCheckoutPolicy(
            allowed_hosts=frozenset(),
            allowed_local_roots=(
                tmp_path / "sources",
                tmp_path / "remotes",
            ),
        )
    )
    checkout = await provider.checkout(
        GitCheckoutRequest(str(source), base_sha), workspace=workspace
    )
    await _git(checkout.repository_path, "remote", "set-url", "origin", str(remote))
    generated = checkout.repository_path / "generated.py"
    generated.write_text("value = 1\n", encoding="utf-8")
    committed = await provider.commit_validated(
        GitCommitRequest(
            expected_base_sha=base_sha,
            branch_name="autoforge/job-push",
            message="chore: generate service",
            author_name="AutoForge",
            author_email="autoforge@example.invalid",
            allowed_paths=(PurePosixPath("generated.py"),),
        ),
        workspace=workspace,
    )
    request = GitPushRequest(
        expected_commit_sha=committed.commit_sha,
        branch_name="autoforge/job-push",
    )

    first = await provider.push_validated(request, workspace=workspace)
    second = await provider.push_validated(request, workspace=workspace)

    assert first.pushed is True
    assert second.pushed is False
    assert first.commit_sha == committed.commit_sha
    assert second.commit_sha == committed.commit_sha
    assert await _git(remote, "rev-parse", "refs/heads/autoforge/job-push") == (
        committed.commit_sha
    )
    with pytest.raises(ValueError, match="protected"):
        await provider.push_validated(
            GitPushRequest(
                expected_commit_sha=committed.commit_sha,
                branch_name="main",
            ),
            workspace=workspace,
        )

    collaborator = tmp_path / "collaborator"
    await _git(tmp_path, "clone", str(remote), str(collaborator))
    await _git(collaborator, "checkout", "autoforge/job-push")
    await _git(collaborator, "config", "user.name", "Collaborator")
    await _git(
        collaborator, "config", "user.email", "collaborator@example.invalid"
    )
    (collaborator / "remote.py").write_text("remote = 1\n", encoding="utf-8")
    await _git(collaborator, "add", "remote.py")
    await _git(collaborator, "commit", "-m", "remote advance")
    await _git(collaborator, "push", "origin", "autoforge/job-push")
    remote_sha = await _git(collaborator, "rev-parse", "HEAD")
    await _git(checkout.repository_path, "config", "user.name", "Local")
    await _git(
        checkout.repository_path,
        "config",
        "user.email",
        "local@example.invalid",
    )
    (checkout.repository_path / "local.py").write_text(
        "local = 1\n", encoding="utf-8"
    )
    await _git(checkout.repository_path, "add", "local.py")
    await _git(checkout.repository_path, "commit", "-m", "local advance")
    local_sha = await _git(checkout.repository_path, "rev-parse", "HEAD")

    with pytest.raises(GitProviderError, match="push validated commit"):
        await provider.push_validated(
            GitPushRequest(
                expected_commit_sha=local_sha,
                branch_name="autoforge/job-push",
            ),
            workspace=workspace,
        )

    assert await _git(remote, "rev-parse", "refs/heads/autoforge/job-push") == (
        remote_sha
    )
