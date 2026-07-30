import json
from pathlib import Path

import pytest

from autoforge.core.generation import (
    FileOwnership,
    FileResultStatus,
    GenerationManifest,
    ManifestFile,
    content_hash,
)
from autoforge.core.job import (
    GenerationJobManifest,
    GenerationUnitKind,
    GenerationUnitManifest,
)
from autoforge.core.workspace import Workspace
from autoforge.services.generation import (
    MANIFEST_RELATIVE_PATH,
    ManifestStore,
    ManifestStoreError,
)

SPECIFICATION_HASH = content_hash("명세")
CONTENT_HASH = content_hash("생성 내용")


def manifest() -> GenerationManifest:
    return GenerationManifest(
        job_id="job-001",
        specification_version="1",
        specification_hash=SPECIFICATION_HASH,
        files=[
            ManifestFile(
                relative_path="src/game_server/main.py",
                generator_id="autoforge.generator.fastapi.project",
                generator_version="0.1.0",
                ownership=FileOwnership.GENERATED,
                status=FileResultStatus.CREATED,
                specification_hash=SPECIFICATION_HASH,
                content_hash=CONTENT_HASH,
                source="project:게임서버",
            )
        ],
    )


def job_manifest() -> GenerationJobManifest:
    return GenerationJobManifest(
        job_id="job-001",
        units=[
            GenerationUnitManifest(
                unit_id="project:game_server",
                kind=GenerationUnitKind.PROJECT,
                manifest=manifest(),
            )
        ],
    )


def test_save_and_load_manifest_round_trip(tmp_path: Path) -> None:
    store = ManifestStore(Workspace(tmp_path))
    original = manifest()

    saved_path = store.save(original)
    loaded = store.load()

    assert saved_path == tmp_path / ".autoforge" / "manifest.json"
    assert (
        saved_path.relative_to(tmp_path).as_posix() == MANIFEST_RELATIVE_PATH.as_posix()
    )
    assert loaded == original


def test_save_is_deterministic_utf8_json(tmp_path: Path) -> None:
    store = ManifestStore(Workspace(tmp_path))
    original = manifest()

    store.save(original)
    first = store.path.read_bytes()
    store.save(original)
    second = store.path.read_bytes()

    assert first == second
    assert first.endswith(b"\n")
    assert "게임서버" in first.decode("utf-8")
    assert "\\u" not in first.decode("utf-8")
    assert json.loads(first)["job_id"] == "job-001"


def test_save_replaces_existing_manifest(tmp_path: Path) -> None:
    store = ManifestStore(Workspace(tmp_path))
    store.save(manifest())
    changed = manifest().model_copy(update={"job_id": "job-002"})

    store.save(changed)

    assert store.load().job_id == "job-002"
    assert not (tmp_path / ".autoforge" / "manifest.json.tmp").exists()


def test_save_and_load_job_manifest_round_trip(tmp_path: Path) -> None:
    store = ManifestStore(Workspace(tmp_path))
    original = job_manifest()

    store.save_job(original)

    assert store.load_job() == original
    assert store.load_any() == original


def test_save_job_manifest_is_deterministic_versioned_json(tmp_path: Path) -> None:
    store = ManifestStore(Workspace(tmp_path))
    original = job_manifest()

    store.save_job(original)
    first = store.path.read_bytes()
    store.save_job(original)

    assert store.path.read_bytes() == first
    assert json.loads(first)["document_kind"] == "generation_job"
    assert json.loads(first)["format_version"] == "1"


def test_load_any_preserves_legacy_manifest_compatibility(tmp_path: Path) -> None:
    store = ManifestStore(Workspace(tmp_path))
    store.save(manifest())

    loaded = store.load_any()

    assert isinstance(loaded, GenerationManifest)
    assert loaded == manifest()


def test_typed_loaders_reject_other_manifest_kind(tmp_path: Path) -> None:
    store = ManifestStore(Workspace(tmp_path))
    store.save_job(job_manifest())

    with pytest.raises(ManifestStoreError, match="기존 GenerationManifest"):
        store.load()

    store.save(manifest())
    with pytest.raises(ManifestStoreError, match="GenerationJobManifest"):
        store.load_job()


@pytest.mark.parametrize(
    "updates",
    [
        {"format_version": "999"},
        {"document_kind": "unknown"},
        {"document_kind": None},
    ],
)
def test_load_rejects_unknown_or_mixed_job_manifest(
    tmp_path: Path,
    updates: dict[str, str | None],
) -> None:
    target = tmp_path / ".autoforge" / "manifest.json"
    target.parent.mkdir()
    data = job_manifest().model_dump(mode="json")
    if updates.get("document_kind", ...) is None:
        data.pop("document_kind")
    else:
        data.update(updates)
    target.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ManifestStoreError, match="유효하지"):
        ManifestStore(Workspace(tmp_path)).load_any()


@pytest.mark.parametrize(
    "content",
    [
        b"{not json",
        json.dumps({"job_id": "missing fields"}).encode("utf-8"),
        b"\xff",
    ],
)
def test_load_rejects_invalid_manifest(tmp_path: Path, content: bytes) -> None:
    target = tmp_path / ".autoforge" / "manifest.json"
    target.parent.mkdir()
    target.write_bytes(content)

    with pytest.raises(ManifestStoreError, match="유효하지"):
        ManifestStore(Workspace(tmp_path)).load()


def test_load_rejects_missing_manifest(tmp_path: Path) -> None:
    with pytest.raises(ManifestStoreError, match="찾을 수 없습니다"):
        ManifestStore(Workspace(tmp_path)).load()


def test_save_rejects_directory_at_manifest_path(tmp_path: Path) -> None:
    (tmp_path / ".autoforge" / "manifest.json").mkdir(parents=True)

    with pytest.raises(ManifestStoreError, match="파일이 아닙니다"):
        ManifestStore(Workspace(tmp_path)).save(manifest())
