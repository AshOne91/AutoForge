from typing import Protocol

from autoforge.core.git.models import (
    GitCheckoutRequest,
    GitCheckoutResult,
    GitCommitRequest,
    GitCommitResult,
    GitPushRequest,
    GitPushResult,
)
from autoforge.core.workspace import Workspace


class GitProvider(Protocol):
    async def checkout(
        self, request: GitCheckoutRequest, *, workspace: Workspace
    ) -> GitCheckoutResult: ...

    async def commit_validated(
        self, request: GitCommitRequest, *, workspace: Workspace
    ) -> GitCommitResult: ...

    async def push_validated(
        self, request: GitPushRequest, *, workspace: Workspace
    ) -> GitPushResult: ...
