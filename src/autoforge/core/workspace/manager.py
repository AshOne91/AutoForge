from contextlib import AbstractAsyncContextManager
from typing import Protocol

from autoforge.core.workspace.workspace import Workspace


class WorkspaceManager(Protocol):
    def create(self, workspace_name: str) -> AbstractAsyncContextManager[Workspace]: ...
