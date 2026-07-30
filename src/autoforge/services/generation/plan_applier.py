from collections.abc import Mapping
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


class GenerationPlanApplyError(RuntimeError):
    """GenerationPlan을 안전하게 적용할 수 없을 때 발생한다."""


class GenerationPlanApplier:
    """검증된 생성 계획을 Workspace에 적용하고 실행 결과를 반환한다."""

    def apply(
        self,
        *,
        job_id: str,
        plan: GenerationPlan,
        rendered_files: Mapping[PurePosixPath, str],
        workspace: Workspace,
    ) -> GenerationManifest:
        normalized_rendered = self._validate_rendered_files(plan, rendered_files)
        targets = {
            planned_file.relative_path: workspace.resolve(planned_file.relative_path)
            for planned_file in plan.files
        }
        self._preflight(plan, normalized_rendered, targets)

        manifest_files = [
            self._apply_file(
                planned_file,
                normalized_rendered[planned_file.relative_path],
                targets[planned_file.relative_path],
            )
            for planned_file in plan.files
        ]
        return GenerationManifest(
            job_id=job_id,
            specification_version=plan.specification_version,
            specification_hash=plan.specification_hash,
            files=manifest_files,
        )

    @staticmethod
    def _validate_rendered_files(
        plan: GenerationPlan,
        rendered_files: Mapping[PurePosixPath, str],
    ) -> dict[PurePosixPath, str]:
        normalized = {
            PurePosixPath(relative_path): content
            for relative_path, content in rendered_files.items()
        }
        planned_paths = {planned_file.relative_path for planned_file in plan.files}
        rendered_paths = set(normalized)
        if planned_paths != rendered_paths:
            missing = sorted(path.as_posix() for path in planned_paths - rendered_paths)
            unexpected = sorted(
                path.as_posix() for path in rendered_paths - planned_paths
            )
            raise GenerationPlanApplyError(
                f"계획과 렌더링 경로가 일치하지 않습니다. "
                f"누락={missing}, 추가={unexpected}"
            )

        for planned_file in plan.files:
            if planned_file.specification_hash != plan.specification_hash:
                raise GenerationPlanApplyError(
                    f"계획 파일의 명세 Hash가 일치하지 않습니다: "
                    f"{planned_file.relative_path.as_posix()}"
                )
            rendered_hash = content_hash(normalized[planned_file.relative_path])
            if rendered_hash != planned_file.expected_content_hash:
                raise GenerationPlanApplyError(
                    f"렌더링 내용 Hash가 계획과 일치하지 않습니다: "
                    f"{planned_file.relative_path.as_posix()}"
                )
        return normalized

    def _preflight(
        self,
        plan: GenerationPlan,
        rendered_files: Mapping[PurePosixPath, str],
        targets: Mapping[PurePosixPath, Path],
    ) -> None:
        conflicts = [
            planned_file.relative_path.as_posix()
            for planned_file in plan.files
            if planned_file.action is PlannedAction.CONFLICT
        ]
        if conflicts:
            raise GenerationPlanApplyError(
                f"충돌이 있어 파일을 적용할 수 없습니다: {sorted(conflicts)}"
            )

        for planned_file in plan.files:
            target = targets[planned_file.relative_path]
            self._validate_current_state(
                planned_file,
                rendered_files[planned_file.relative_path],
                target,
            )

    def _validate_current_state(
        self,
        planned_file: PlannedFile,
        rendered_content: str,
        target: Path,
    ) -> None:
        action = planned_file.action
        relative_path = planned_file.relative_path.as_posix()

        if action is PlannedAction.REPLACE_GENERATED:
            raise GenerationPlanApplyError(
                f"안전한 교체 정책이 아직 정의되지 않았습니다: {relative_path}"
            )
        if action is PlannedAction.CREATE:
            if target.exists():
                raise GenerationPlanApplyError(
                    f"CREATE 대상이 이미 존재합니다: {relative_path}"
                )
            self._validate_parent_directories(target)
            return
        if action is PlannedAction.SKIP:
            if target.exists():
                raise GenerationPlanApplyError(
                    f"SKIP 대상이 계획 이후 생성되었습니다: {relative_path}"
                )
            return
        if action is not PlannedAction.KEEP:
            raise GenerationPlanApplyError(
                f"지원하지 않는 계획 작업입니다: {action.value}"
            )
        if not target.is_file():
            raise GenerationPlanApplyError(
                f"KEEP 대상 파일을 찾을 수 없습니다: {relative_path}"
            )
        if planned_file.ownership is FileOwnership.GENERATED:
            actual_hash = content_hash(target.read_bytes())
            if actual_hash != content_hash(rendered_content):
                raise GenerationPlanApplyError(
                    f"GENERATED 파일이 계획 이후 변경되었습니다: {relative_path}"
                )

    @staticmethod
    def _validate_parent_directories(target: Path) -> None:
        for parent in target.parents:
            if parent.exists() and not parent.is_dir():
                raise GenerationPlanApplyError(
                    f"부모 경로가 디렉터리가 아닙니다: {parent}"
                )

    @staticmethod
    def _apply_file(
        planned_file: PlannedFile,
        rendered_content: str,
        target: Path,
    ) -> ManifestFile:
        action = planned_file.action
        previous_hash = content_hash(target.read_bytes()) if target.is_file() else None

        if action is PlannedAction.CREATE:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(rendered_content.encode("utf-8"))
            status = FileResultStatus.CREATED
            result_hash = content_hash(target.read_bytes())
        elif action is PlannedAction.KEEP:
            status = (
                FileResultStatus.UNCHANGED
                if planned_file.ownership is FileOwnership.GENERATED
                else FileResultStatus.PRESERVED
            )
            result_hash = previous_hash
        else:
            status = FileResultStatus.SKIPPED
            result_hash = None

        return ManifestFile(
            relative_path=planned_file.relative_path,
            generator_id=planned_file.generator_id,
            generator_version=planned_file.generator_version,
            ownership=planned_file.ownership,
            status=status,
            specification_hash=planned_file.specification_hash,
            previous_content_hash=previous_hash,
            content_hash=result_hash,
            source=planned_file.source,
        )
