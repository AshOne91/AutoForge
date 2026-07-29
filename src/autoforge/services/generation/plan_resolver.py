from pathlib import Path

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
)
from autoforge.core.workspace import Workspace


class GenerationPlanResolver:
    def resolve(
        self,
        plan: GenerationPlan,
        workspace: Workspace,
    ) -> GenerationPlan:
        resolved_files = [
            self._resolve_file(planned_file, workspace) for planned_file in plan.files
        ]
        return plan.model_copy(update={"files": resolved_files})

    def _resolve_file(
        self,
        planned_file: PlannedFile,
        workspace: Workspace,
    ) -> PlannedFile:
        target = workspace.resolve(planned_file.relative_path)
        action = self._resolve_action(planned_file, target)
        return planned_file.model_copy(update={"action": action})

    @staticmethod
    def _resolve_action(
        planned_file: PlannedFile,
        target: Path,
    ) -> PlannedAction:
        if not target.exists():
            if planned_file.ownership is FileOwnership.USER_OWNED:
                return PlannedAction.SKIP
            return PlannedAction.CREATE

        if not target.is_file():
            return PlannedAction.CONFLICT

        if planned_file.ownership is FileOwnership.USER_OWNED:
            return PlannedAction.KEEP

        if planned_file.ownership is FileOwnership.SCAFFOLDED:
            return PlannedAction.KEEP

        if content_hash(target.read_bytes()) == planned_file.expected_content_hash:
            return PlannedAction.KEEP

        return PlannedAction.CONFLICT
