from typing import Protocol

from autoforge.core.git.models import GitCheckoutRequest, GitCheckoutResult
from autoforge.core.workspace import Workspace


class GitProvider(Protocol):
    async def checkout(
        self, request: GitCheckoutRequest, *, workspace: Workspace
    ) -> GitCheckoutResult: ...
