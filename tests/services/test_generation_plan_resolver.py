from pathlib import Path

from autoforge.core.generation import (
    FileOwnership,
    GenerationPlan,
    PlannedAction,
    PlannedFile,
    content_hash,
)
from autoforge.core.workspace import Workspace
from autoforge.services.generation import GenerationPlanResolver

SPECIFICATION_HASH = content_hash("specification")


def planned_file(
    relative_path: str,
    *,
    content: str = "generated content",
    ownership: FileOwnership = FileOwnership.GENERATED,
    action: PlannedAction = PlannedAction.CREATE,
) -> PlannedFile:
    return PlannedFile(
        relative_path=relative_path,
        generator_id="autoforge.generator.fastapi.project",
        generator_version="0.1.0",
        ownership=ownership,
        action=action,
        specification_hash=SPECIFICATION_HASH,
        expected_content_hash=content_hash(content),
        source="project:game_server",
    )


def generation_plan(*files: PlannedFile) -> GenerationPlan:
    return GenerationPlan(
        specification_version="1",
        specification_hash=SPECIFICATION_HASH,
        files=list(files),
    )


def test_missing_files_remain_create_actions(tmp_path: Path) -> None:
    original = generation_plan(
        planned_file("src/game_server/main.py"),
        planned_file(
            "README.md",
            ownership=FileOwnership.SCAFFOLDED,
        ),
    )

    resolved = GenerationPlanResolver().resolve(original, Workspace(tmp_path))

    assert [file.action for file in resolved.files] == [
        PlannedAction.CREATE,
        PlannedAction.CREATE,
    ]


def test_identical_generated_file_is_kept(tmp_path: Path) -> None:
    content = "generated content"
    target = tmp_path / "src" / "game_server" / "main.py"
    target.parent.mkdir(parents=True)
    target.write_text(content, encoding="utf-8")
    original = generation_plan(planned_file("src/game_server/main.py", content=content))

    resolved = GenerationPlanResolver().resolve(original, Workspace(tmp_path))

    assert resolved.files[0].action is PlannedAction.KEEP


def test_modified_generated_file_is_a_conflict(tmp_path: Path) -> None:
    target = tmp_path / "src" / "game_server" / "main.py"
    target.parent.mkdir(parents=True)
    target.write_text("manual change", encoding="utf-8")
    original = generation_plan(planned_file("src/game_server/main.py"))

    resolved = GenerationPlanResolver().resolve(original, Workspace(tmp_path))

    assert resolved.files[0].action is PlannedAction.CONFLICT


def test_existing_scaffolded_file_is_kept(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("user documentation", encoding="utf-8")
    original = generation_plan(
        planned_file("README.md", ownership=FileOwnership.SCAFFOLDED)
    )

    resolved = GenerationPlanResolver().resolve(original, Workspace(tmp_path))

    assert resolved.files[0].action is PlannedAction.KEEP
    assert target.read_text(encoding="utf-8") == "user documentation"


def test_directory_at_file_path_is_a_conflict(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").mkdir()
    original = generation_plan(planned_file("pyproject.toml"))

    resolved = GenerationPlanResolver().resolve(original, Workspace(tmp_path))

    assert resolved.files[0].action is PlannedAction.CONFLICT


def test_user_owned_directory_at_file_path_is_a_conflict(tmp_path: Path) -> None:
    (tmp_path / "custom.py").mkdir()
    original = generation_plan(
        planned_file(
            "custom.py",
            ownership=FileOwnership.USER_OWNED,
            action=PlannedAction.SKIP,
        )
    )

    resolved = GenerationPlanResolver().resolve(original, Workspace(tmp_path))

    assert resolved.files[0].action is PlannedAction.CONFLICT


def test_user_owned_file_is_never_created(tmp_path: Path) -> None:
    missing_plan = generation_plan(
        planned_file(
            "custom.py",
            ownership=FileOwnership.USER_OWNED,
            action=PlannedAction.SKIP,
        )
    )

    missing_result = GenerationPlanResolver().resolve(
        missing_plan,
        Workspace(tmp_path),
    )
    (tmp_path / "custom.py").write_text("user content", encoding="utf-8")
    existing_result = GenerationPlanResolver().resolve(
        missing_plan,
        Workspace(tmp_path),
    )

    assert missing_result.files[0].action is PlannedAction.SKIP
    assert existing_result.files[0].action is PlannedAction.KEEP


def test_resolver_does_not_mutate_original_plan(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("user documentation", encoding="utf-8")
    original = generation_plan(
        planned_file("README.md", ownership=FileOwnership.SCAFFOLDED)
    )

    resolved = GenerationPlanResolver().resolve(original, Workspace(tmp_path))

    assert original.files[0].action is PlannedAction.CREATE
    assert resolved.files[0].action is PlannedAction.KEEP
    assert resolved is not original


def test_resolver_does_not_change_workspace_contents(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("user documentation", encoding="utf-8")
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    original = generation_plan(
        planned_file("README.md", ownership=FileOwnership.SCAFFOLDED),
        planned_file("src/game_server/main.py"),
    )

    GenerationPlanResolver().resolve(original, Workspace(tmp_path))

    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before
