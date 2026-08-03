from pathlib import Path

from autoforge.core.git import (
    GitCheckoutPolicy,
    GitCheckoutRequest,
    GitCheckoutResult,
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


def test_git_provider_contract_is_infrastructure_independent(tmp_path: Path) -> None:
    provider: GitProvider = StubGitProvider()
    request = GitCheckoutRequest("https://github.com/example/repo.git", "main")
    policy = GitCheckoutPolicy(allowed_hosts=frozenset({"github.com"}))

    assert provider is not None
    assert request.destination == "repository"
    assert policy.allowed_hosts == frozenset({"github.com"})
