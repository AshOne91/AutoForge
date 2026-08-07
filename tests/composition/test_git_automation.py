import asyncio

import httpx
import pytest

from autoforge.composition import create_git_automation_components
from autoforge.core.config import GitAutomationConfig
from autoforge.core.git import GitPullRequestRequest
from autoforge.core.secret import SecretReference


def test_disabled_git_automation_does_not_create_components() -> None:
    assert create_git_automation_components(GitAutomationConfig()) is None


def test_git_automation_components_share_validated_policy_and_settings() -> None:
    config = GitAutomationConfig(
        enabled=True,
        secret_names={"git/github/token": "AUTOFORGE_GITHUB_TOKEN"},
        branch_prefix="generated",
        protected_branches=frozenset({"main"}),
        pull_request_base_branch="main",
        author_name="AutoForge Bot",
        author_email="autoforge@example.test",
    )
    components = create_git_automation_components(
        config,
        environment={"AUTOFORGE_GITHUB_TOKEN": "test-token"},
        github_transport=httpx.MockTransport(
            lambda request: httpx.Response(500, request=request)
        ),
    )

    assert components is not None
    assert components.git_commit_settings.branch_prefix == "generated"
    assert components.git_push_settings.remote_name == "origin"
    assert components.pull_request_settings.base_branch == "main"

    request = GitPullRequestRequest(
        repository_url="https://github.com/AshOne91/example.git",
        expected_head_sha="a" * 40,
        head_branch="feature/not-generated",
        base_branch="main",
        title="Generate project",
        body="",
        credential=SecretReference("git/github/token"),
    )
    try:
        with pytest.raises(ValueError, match="head branch is not allowed"):
            asyncio.run(components.pull_request_provider.create_or_get(request))
    finally:
        asyncio.run(components.aclose())
