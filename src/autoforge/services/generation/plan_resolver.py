from pathlib import Path, PurePosixPath

from autoforge.core.generation import (
    FileOwnership,
    FileResultStatus,
    GenerationManifest,
    GenerationPlan,
    ManifestFile,
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
        manifest: GenerationManifest | None = None,
    ) -> GenerationPlan:
        manifest_files = (
            {file.relative_path: file for file in manifest.files}
            if manifest is not None
            else {}
        )
        resolved_files = [
            self._resolve_file(planned_file, workspace, manifest_files)
            for planned_file in plan.files
        ]
        return plan.model_copy(update={"files": resolved_files})

    def _resolve_file(
        self,
        planned_file: PlannedFile,
        workspace: Workspace,
        manifest_files: dict[PurePosixPath, ManifestFile],
    ) -> PlannedFile:
        target = workspace.resolve(planned_file.relative_path)
        action, previous_hash = self._resolve_action(
            planned_file,
            target,
            manifest_files.get(planned_file.relative_path),
        )
        return planned_file.model_copy(
            update={
                "action": action,
                "previous_content_hash": previous_hash,
            }
        )

    @staticmethod
    def _resolve_action(
        planned_file: PlannedFile,
        target: Path,
        manifest_file: ManifestFile | None,
    ) -> tuple[PlannedAction, str | None]:
        if not target.exists():
            if planned_file.ownership is FileOwnership.USER_OWNED:
                return PlannedAction.SKIP, None
            return PlannedAction.CREATE, None

        if not target.is_file():
            return PlannedAction.CONFLICT, None

        if planned_file.ownership is FileOwnership.USER_OWNED:
            return PlannedAction.KEEP, None

        if planned_file.ownership is FileOwnership.SCAFFOLDED:
            return PlannedAction.KEEP, None

        actual_hash = content_hash(target.read_bytes())
        if actual_hash == planned_file.expected_content_hash:
            return PlannedAction.KEEP, None

        if GenerationPlanResolver._can_replace(
            planned_file,
            manifest_file,
            actual_hash,
        ):
            return PlannedAction.REPLACE_GENERATED, actual_hash
        return PlannedAction.CONFLICT, None

    @staticmethod
    def _can_replace(
        planned_file: PlannedFile,
        manifest_file: ManifestFile | None,
        actual_hash: str,
    ) -> bool:
        return (
            manifest_file is not None
            and manifest_file.ownership is FileOwnership.GENERATED
            and manifest_file.status
            in {
                FileResultStatus.CREATED,
                FileResultStatus.CHANGED,
                FileResultStatus.UNCHANGED,
            }
            and manifest_file.generator_id == planned_file.generator_id
            and manifest_file.source == planned_file.source
            and manifest_file.content_hash == actual_hash
        )
