import pytest
from pydantic import ValidationError

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

SPECIFICATION_HASH = content_hash("specification")
CONTENT_HASH = content_hash("content")


def planned_file(**overrides: object) -> PlannedFile:
    values: dict[str, object] = {
        "relative_path": "src/game_server/generated/router.py",
        "generator_id": "autoforge.generator.fastapi",
        "generator_version": "0.1.0",
        "ownership": FileOwnership.GENERATED,
        "action": PlannedAction.CREATE,
        "specification_hash": SPECIFICATION_HASH,
        "expected_content_hash": CONTENT_HASH,
        "source": "module:tutorial",
    }
    values.update(overrides)
    return PlannedFile.model_validate(values)


def manifest_file(**overrides: object) -> ManifestFile:
    values: dict[str, object] = {
        "relative_path": "src/game_server/generated/router.py",
        "generator_id": "autoforge.generator.fastapi",
        "generator_version": "0.1.0",
        "ownership": FileOwnership.GENERATED,
        "status": FileResultStatus.CREATED,
        "specification_hash": SPECIFICATION_HASH,
        "content_hash": CONTENT_HASH,
        "source": "module:tutorial",
    }
    values.update(overrides)
    return ManifestFile.model_validate(values)


def test_generation_plan_accepts_valid_files() -> None:
    plan = GenerationPlan(
        specification_version="1",
        specification_hash=SPECIFICATION_HASH,
        files=[
            planned_file(),
            planned_file(
                relative_path="src/game_server/modules/tutorial/handlers.py",
                ownership=FileOwnership.SCAFFOLDED,
            ),
        ],
    )

    assert len(plan.files) == 2
    assert plan.files[0].relative_path.as_posix().endswith("router.py")


@pytest.mark.parametrize(
    "relative_path",
    [
        "/absolute/router.py",
        "C:/absolute/router.py",
        "../outside.py",
        "src/../outside.py",
        r"src\game_server\router.py",
        "",
    ],
)
def test_planned_file_rejects_unsafe_paths(relative_path: str) -> None:
    with pytest.raises(ValidationError):
        planned_file(relative_path=relative_path)


def test_generation_plan_rejects_duplicate_paths() -> None:
    with pytest.raises(ValidationError, match="중복"):
        GenerationPlan(
            specification_version="1",
            specification_hash=SPECIFICATION_HASH,
            files=[planned_file(), planned_file()],
        )


def test_user_owned_file_cannot_be_created() -> None:
    with pytest.raises(ValidationError, match="USER_OWNED"):
        planned_file(
            ownership=FileOwnership.USER_OWNED,
            action=PlannedAction.CREATE,
        )


def test_only_generated_file_can_be_replaced() -> None:
    with pytest.raises(ValidationError, match="GENERATED"):
        planned_file(
            ownership=FileOwnership.SCAFFOLDED,
            action=PlannedAction.REPLACE_GENERATED,
            previous_content_hash=CONTENT_HASH,
        )


def test_replace_generated_requires_previous_content_hash() -> None:
    with pytest.raises(ValidationError, match="previous_content_hash"):
        planned_file(action=PlannedAction.REPLACE_GENERATED)


def test_non_replace_action_rejects_previous_content_hash() -> None:
    with pytest.raises(ValidationError, match="previous_content_hash"):
        planned_file(previous_content_hash=CONTENT_HASH)


def test_manifest_accepts_file_results() -> None:
    manifest = GenerationManifest(
        job_id="job-001",
        specification_version="1",
        specification_hash=SPECIFICATION_HASH,
        files=[manifest_file()],
    )

    assert manifest.files[0].status is FileResultStatus.CREATED


def test_failed_manifest_file_requires_error() -> None:
    with pytest.raises(ValidationError, match="error"):
        manifest_file(status=FileResultStatus.FAILED, content_hash=None)


def test_non_failed_manifest_file_rejects_error() -> None:
    with pytest.raises(ValidationError, match="error"):
        manifest_file(error="unexpected")


def test_models_reject_invalid_hashes() -> None:
    with pytest.raises(ValidationError, match="SHA-256"):
        planned_file(specification_hash="not-a-hash")
