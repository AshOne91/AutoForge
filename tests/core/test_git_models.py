from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.git import (
    GitCheckoutPolicy,
    GitCheckoutRequest,
    GitCheckoutResult,
    GitCommitRequest,
    GitCommitResult,
    GitProvider,
)
from autoforge.core.workspace import Workspace


class StubGitProvider:
    async def checkout(
        self, request: GitCheckoutRequest, *, workspace: Workspace
    ) -> GitCheckoutResult:
        return GitCheckoutResult(
            repository_path=workspace.resolve(request.destination),
            commit_sha="a" * 40,
            remote_url=request.repository_url,
        )

    async def commit_validated(
        self, request: GitCommitRequest, *, workspace: Workspace
    ) -> GitCommitResult:
        return GitCommitResult(
            commit_sha=request.expected_base_sha,
            branch_name=None,
            changed_paths=(),
            commit_created=False,
        )


def test_git_provider_contract_is_infrastructure_independent(tmp_path: Path) -> None:
    provider: GitProvider = StubGitProvider()
    request = GitCheckoutRequest("https://github.com/example/repo.git", "main")
    policy = GitCheckoutPolicy(allowed_hosts=frozenset({"github.com"}))

    assert provider is not None
    assert request.destination == "repository"
    assert policy.allowed_hosts == frozenset({"github.com"})


def test_git_commit_request_normalizes_and_rejects_unsafe_paths() -> None:
    request = GitCommitRequest(
        expected_base_sha="a" * 40,
        branch_name="autoforge/job-1",
        message="chore: generate service",
        author_name="AutoForge",
        author_email="autoforge@example.invalid",
        allowed_paths=(PurePosixPath("src/service.py"),),
    )

    assert request.allowed_paths == (PurePosixPath("src/service.py"),)

    with pytest.raises(ValueError, match="Workspace"):
        GitCommitRequest(
            expected_base_sha="a" * 40,
            branch_name="autoforge/job-1",
            message="chore: generate service",
            author_name="AutoForge",
            author_email="autoforge@example.invalid",
            allowed_paths=(PurePosixPath("../outside.py"),),
        )

    with pytest.raises(ValueError, match="unique"):
        GitCommitRequest(
            expected_base_sha="a" * 40,
            branch_name="autoforge/job-1",
            message="chore: generate service",
            author_name="AutoForge",
            author_email="autoforge@example.invalid",
            allowed_paths=(PurePosixPath("same.py"), PurePosixPath("same.py")),
        )
