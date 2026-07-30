from pathlib import Path, PurePosixPath

import pytest

from autoforge.core.generation import (
    FileOwnership,
    FileResultStatus,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
)
from autoforge.core.specification import ApplicationSpec, ProjectInfo, ProjectSpec
from autoforge.core.workspace import Workspace
from autoforge.services.generation import (
    FastAPIProjectGenerator,
    GenerationPlanApplier,
    GenerationPlanApplyError,
    GenerationPlanResolver,
)

SPECIFICATION_HASH = content_hash("specification")


def planned_file(
    relative_path: str,
    content: str,
    *,
    ownership: FileOwnership = FileOwnership.GENERATED,
    action: PlannedAction = PlannedAction.CREATE,
    specification_hash: str = SPECIFICATION_HASH,
) -> PlannedFile:
    return PlannedFile(
        relative_path=relative_path,
        generator_id="autoforge.generator.fastapi.project",
        generator_version="0.1.0",
        ownership=ownership,
        action=action,
        specification_hash=specification_hash,
        expected_content_hash=content_hash(content),
        source="project:game_server",
    )


def generation_plan(*files: PlannedFile) -> GenerationPlan:
    return GenerationPlan(
        specification_version="1",
        specification_hash=SPECIFICATION_HASH,
        files=list(files),
    )


def apply(
    tmp_path: Path,
    plan: GenerationPlan,
    rendered_files: dict[PurePosixPath, str],
):
    return GenerationPlanApplier().apply(
        job_id="job-001",
        plan=plan,
        rendered_files=rendered_files,
        workspace=Workspace(tmp_path),
    )


def test_create_files_and_return_manifest(tmp_path: Path) -> None:
    main_content = "app = object()\n"
    readme_content = "# Game Server\n"
    plan = generation_plan(
        planned_file("src/game_server/main.py", main_content),
        planned_file(
            "README.md",
            readme_content,
            ownership=FileOwnership.SCAFFOLDED,
        ),
    )

    manifest = apply(
        tmp_path,
        plan,
        {
            PurePosixPath("src/game_server/main.py"): main_content,
            PurePosixPath("README.md"): readme_content,
        },
    )

    assert (tmp_path / "src/game_server/main.py").read_text(
        encoding="utf-8"
    ) == main_content
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == readme_content
    assert manifest.job_id == "job-001"
    assert [file.status for file in manifest.files] == [
        FileResultStatus.CREATED,
        FileResultStatus.CREATED,
    ]
    assert all(file.previous_content_hash is None for file in manifest.files)


def test_conflict_aborts_before_any_file_is_written(tmp_path: Path) -> None:
    rendered = {
        PurePosixPath("first.py"): "first\n",
        PurePosixPath("conflict.py"): "generated\n",
    }
    plan = generation_plan(
        planned_file("first.py", rendered[PurePosixPath("first.py")]),
        planned_file(
            "conflict.py",
            rendered[PurePosixPath("conflict.py")],
            action=PlannedAction.CONFLICT,
        ),
    )

    with pytest.raises(GenerationPlanApplyError, match="충돌"):
        apply(tmp_path, plan, rendered)

    assert not (tmp_path / "first.py").exists()
    assert not (tmp_path / "conflict.py").exists()


@pytest.mark.parametrize(
    ("plan", "rendered", "message"),
    [
        (
            generation_plan(planned_file("main.py", "planned\n")),
            {PurePosixPath("other.py"): "planned\n"},
            "경로",
        ),
        (
            generation_plan(planned_file("main.py", "planned\n")),
            {PurePosixPath("main.py"): "different\n"},
            "내용 Hash",
        ),
        (
            generation_plan(
                planned_file(
                    "main.py",
                    "planned\n",
                    specification_hash=content_hash("different specification"),
                )
            ),
            {PurePosixPath("main.py"): "planned\n"},
            "명세 Hash",
        ),
    ],
)
def test_rejects_plan_and_rendering_mismatch(
    tmp_path: Path,
    plan: GenerationPlan,
    rendered: dict[PurePosixPath, str],
    message: str,
) -> None:
    with pytest.raises(GenerationPlanApplyError, match=message):
        apply(tmp_path, plan, rendered)

    assert list(tmp_path.iterdir()) == []


def test_keep_and_skip_preserve_workspace(tmp_path: Path) -> None:
    generated_content = "generated\n"
    scaffolded_content = "user edited documentation\n"
    (tmp_path / "generated.py").write_bytes(generated_content.encode("utf-8"))
    (tmp_path / "README.md").write_text(scaffolded_content, encoding="utf-8")
    plan = generation_plan(
        planned_file(
            "generated.py",
            generated_content,
            action=PlannedAction.KEEP,
        ),
        planned_file(
            "README.md",
            "initial documentation\n",
            ownership=FileOwnership.SCAFFOLDED,
            action=PlannedAction.KEEP,
        ),
        planned_file(
            "custom.py",
            "",
            ownership=FileOwnership.USER_OWNED,
            action=PlannedAction.SKIP,
        ),
    )

    manifest = apply(
        tmp_path,
        plan,
        {
            PurePosixPath("generated.py"): generated_content,
            PurePosixPath("README.md"): "initial documentation\n",
            PurePosixPath("custom.py"): "",
        },
    )

    assert (tmp_path / "generated.py").read_text(encoding="utf-8") == generated_content
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == scaffolded_content
    assert not (tmp_path / "custom.py").exists()
    assert [file.status for file in manifest.files] == [
        FileResultStatus.UNCHANGED,
        FileResultStatus.PRESERVED,
        FileResultStatus.SKIPPED,
    ]
    assert manifest.files[1].content_hash == content_hash(
        (tmp_path / "README.md").read_bytes()
    )


def test_workspace_change_after_planning_aborts_all_writes(tmp_path: Path) -> None:
    (tmp_path / "existing.py").write_text("changed later\n", encoding="utf-8")
    rendered = {
        PurePosixPath("new.py"): "new\n",
        PurePosixPath("existing.py"): "expected\n",
    }
    plan = generation_plan(
        planned_file("new.py", "new\n"),
        planned_file(
            "existing.py",
            "expected\n",
            action=PlannedAction.KEEP,
        ),
    )

    with pytest.raises(GenerationPlanApplyError, match="계획 이후 변경"):
        apply(tmp_path, plan, rendered)

    assert not (tmp_path / "new.py").exists()
    assert (tmp_path / "existing.py").read_text(encoding="utf-8") == "changed later\n"


def test_create_aborts_when_parent_is_a_file(tmp_path: Path) -> None:
    (tmp_path / "src").write_text("not a directory", encoding="utf-8")
    rendered = {PurePosixPath("src/game_server/main.py"): "app = object()\n"}
    plan = generation_plan(
        planned_file(
            "src/game_server/main.py",
            rendered[PurePosixPath("src/game_server/main.py")],
        )
    )

    with pytest.raises(GenerationPlanApplyError, match="부모 경로"):
        apply(tmp_path, plan, rendered)


def test_replace_generated_is_rejected_until_policy_is_defined(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text("old\n", encoding="utf-8")
    rendered = {PurePosixPath("main.py"): "new\n"}
    plan = generation_plan(
        planned_file(
            "main.py",
            "new\n",
            action=PlannedAction.REPLACE_GENERATED,
        )
    )

    with pytest.raises(GenerationPlanApplyError, match="교체 정책"):
        apply(tmp_path, plan, rendered)

    assert (tmp_path / "main.py").read_text(encoding="utf-8") == "old\n"


def test_apply_minimum_fastapi_project_end_to_end(tmp_path: Path) -> None:
    specification = ProjectSpec(
        spec_version="1",
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
            description="모듈형 FastAPI 게임 서버",
        ),
        application=ApplicationSpec(),
    )
    generator = FastAPIProjectGenerator()
    rendered = generator.render(specification)
    resolved_plan = GenerationPlanResolver().resolve(
        generator.plan(specification),
        Workspace(tmp_path),
    )

    manifest = apply(tmp_path, resolved_plan, rendered)

    assert len(manifest.files) == len(rendered)
    assert all(file.status is FileResultStatus.CREATED for file in manifest.files)
    assert {
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*")
        if path.is_file()
    } == {path.as_posix() for path in rendered}
