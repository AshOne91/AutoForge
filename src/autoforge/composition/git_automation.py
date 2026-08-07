from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import httpx

from autoforge.application.generation import (
    GenerationGitCommitSettings,
    GenerationGitPushSettings,
    GenerationPullRequestSettings,
)
from autoforge.core.config import GitAutomationConfig
from autoforge.core.git import GitCheckoutPolicy, GitPullRequestPolicy
from autoforge.infrastructure.git import (
    GitHubPullRequestProvider,
    HttpxGitHubApiClient,
    SubprocessGitProvider,
)
from autoforge.infrastructure.process import AsyncioProcessRunner
from autoforge.infrastructure.secret import EnvironmentSecretProvider


@dataclass(frozen=True, slots=True)
class GitAutomationComponents:
    """Explicitly owned Git automation dependencies for a worker entrypoint."""

    git_provider: SubprocessGitProvider
    git_commit_settings: GenerationGitCommitSettings
    git_push_settings: GenerationGitPushSettings
    pull_request_provider: GitHubPullRequestProvider
    pull_request_settings: GenerationPullRequestSettings
    _github_client: HttpxGitHubApiClient

    async def aclose(self) -> None:
        await self._github_client.aclose()


def create_git_automation_components(
    config: GitAutomationConfig,
    *,
    environment: Mapping[str, str] | None = None,
    process_runner: AsyncioProcessRunner | None = None,
    github_transport: httpx.AsyncBaseTransport | None = None,
) -> GitAutomationComponents | None:
    """Build Git adapters only when deployment configuration enables them."""

    if not config.enabled:
        return None

    secret_provider = EnvironmentSecretProvider(
        secret_names=config.secret_names,
        environment=environment,
    )
    branch_prefix = f"{config.branch_prefix}/"
    git_provider = SubprocessGitProvider(
        policy=GitCheckoutPolicy(
            allowed_hosts=config.allowed_repository_hosts,
            allowed_push_branch_prefixes=(branch_prefix,),
            protected_branches=config.protected_branches,
        ),
        process_runner=process_runner,
        secret_provider=secret_provider,
        timeout_seconds=config.git_command_timeout_seconds,
    )
    github_client = HttpxGitHubApiClient(
        timeout_seconds=config.github_api_timeout_seconds,
        transport=github_transport,
    )
    pull_request_provider = GitHubPullRequestProvider(
        api_client=github_client,
        secret_provider=secret_provider,
        policy=GitPullRequestPolicy(
            allowed_head_branch_prefixes=(branch_prefix,),
            allowed_base_branches=config.protected_branches,
        ),
    )
    return GitAutomationComponents(
        git_provider=git_provider,
        git_commit_settings=GenerationGitCommitSettings(
            author_name=config.author_name,
            author_email=config.author_email,
            branch_prefix=config.branch_prefix,
            commit_message=config.commit_message,
            signing_key=config.signing_key,
        ),
        git_push_settings=GenerationGitPushSettings(
            remote_name=config.push_remote_name,
        ),
        pull_request_provider=pull_request_provider,
        pull_request_settings=GenerationPullRequestSettings(
            base_branch=config.pull_request_base_branch,
            title=config.pull_request_title,
            body=config.pull_request_body,
        ),
        _github_client=github_client,
    )
