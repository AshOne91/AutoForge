import pytest
from pydantic import ValidationError

from autoforge.core.generation import (
    FileOwnership,
    FileResultStatus,
    GenerationManifest,
    ManifestFile,
    content_hash,
)
from autoforge.core.job import (
    GenerationJob,
    GenerationJobManifest,
    GenerationJobStatus,
    GenerationJobSubmission,
    GenerationUnit,
    GenerationUnitKind,
    GenerationUnitManifest,
    ManifestDocumentKind,
)

PROJECT_HASH = content_hash("project specification")
MODULE_HASH = content_hash("module specification")


def unit(
    unit_id: str,
    kind: GenerationUnitKind,
    specification_hash: str,
) -> GenerationUnit:
    return GenerationUnit(
        unit_id=unit_id,
        kind=kind,
        specification_version="1",
        specification_hash=specification_hash,
    )


def manifest(
    job_id: str,
    relative_path: str,
    specification_hash: str,
) -> GenerationManifest:
    return GenerationManifest(
        job_id=job_id,
        specification_version="1",
        specification_hash=specification_hash,
        files=[
            ManifestFile(
                relative_path=relative_path,
                generator_id="autoforge.generator",
                generator_version="0.1.0",
                ownership=FileOwnership.GENERATED,
                status=FileResultStatus.CREATED,
                specification_hash=specification_hash,
                content_hash=content_hash(relative_path),
                source=relative_path,
            )
        ],
    )


def job_manifest(job_id: str = "job-001") -> GenerationJobManifest:
    return GenerationJobManifest(
        job_id=job_id,
        units=[
            GenerationUnitManifest(
                unit_id="project:game_server",
                kind=GenerationUnitKind.PROJECT,
                manifest=manifest(job_id, "pyproject.toml", PROJECT_HASH),
            ),
            GenerationUnitManifest(
                unit_id="module:tutorial",
                kind=GenerationUnitKind.MODULE,
                manifest=manifest(
                    job_id,
                    "src/game_server/modules/tutorial/generated/router.py",
                    MODULE_HASH,
                ),
            ),
        ],
    )


def test_job_manifest_preserves_each_specification_result() -> None:
    result = job_manifest()

    assert result.document_kind is ManifestDocumentKind.GENERATION_JOB
    assert result.format_version == "1"
    assert len(result.units) == 2
    assert result.units[0].manifest.specification_hash == PROJECT_HASH
    assert result.units[1].manifest.specification_hash == MODULE_HASH


def test_job_manifest_rejects_mismatched_job_id() -> None:
    with pytest.raises(ValidationError, match="job_id"):
        GenerationJobManifest(
            job_id="job-001",
            units=[
                GenerationUnitManifest(
                    unit_id="project:game_server",
                    kind=GenerationUnitKind.PROJECT,
                    manifest=manifest(
                        "different-job",
                        "pyproject.toml",
                        PROJECT_HASH,
                    ),
                )
            ],
        )


def test_job_manifest_rejects_duplicate_unit_ids() -> None:
    project_manifest = manifest("job-001", "pyproject.toml", PROJECT_HASH)

    with pytest.raises(ValidationError, match="unit_id"):
        GenerationJobManifest(
            job_id="job-001",
            units=[
                GenerationUnitManifest(
                    unit_id="duplicate",
                    kind=GenerationUnitKind.PROJECT,
                    manifest=project_manifest,
                ),
                GenerationUnitManifest(
                    unit_id="duplicate",
                    kind=GenerationUnitKind.MODULE,
                    manifest=manifest(
                        "job-001",
                        "module.py",
                        MODULE_HASH,
                    ),
                ),
            ],
        )


def test_job_manifest_rejects_duplicate_file_paths() -> None:
    with pytest.raises(ValidationError, match="파일 경로"):
        GenerationJobManifest(
            job_id="job-001",
            units=[
                GenerationUnitManifest(
                    unit_id="project:game_server",
                    kind=GenerationUnitKind.PROJECT,
                    manifest=manifest(
                        "job-001",
                        "shared.py",
                        PROJECT_HASH,
                    ),
                ),
                GenerationUnitManifest(
                    unit_id="module:tutorial",
                    kind=GenerationUnitKind.MODULE,
                    manifest=manifest(
                        "job-001",
                        "shared.py",
                        MODULE_HASH,
                    ),
                ),
            ],
        )


def test_succeeded_job_requires_all_unit_results() -> None:
    units = [
        unit(
            "project:game_server",
            GenerationUnitKind.PROJECT,
            PROJECT_HASH,
        ),
        unit(
            "module:tutorial",
            GenerationUnitKind.MODULE,
            MODULE_HASH,
        ),
    ]

    job = GenerationJob(
        job_id="job-001",
        status=GenerationJobStatus.SUCCEEDED,
        units=units,
        manifest=job_manifest(),
    )

    assert job.status is GenerationJobStatus.SUCCEEDED


def test_succeeded_job_rejects_missing_result() -> None:
    with pytest.raises(ValidationError, match="모든 Unit"):
        GenerationJob(
            job_id="job-001",
            status=GenerationJobStatus.SUCCEEDED,
            units=[
                unit(
                    "project:game_server",
                    GenerationUnitKind.PROJECT,
                    PROJECT_HASH,
                ),
                unit(
                    "module:tutorial",
                    GenerationUnitKind.MODULE,
                    MODULE_HASH,
                ),
            ],
            manifest=GenerationJobManifest(
                job_id="job-001",
                units=[job_manifest().units[0]],
            ),
        )


def test_failed_job_requires_error() -> None:
    with pytest.raises(ValidationError, match="error"):
        GenerationJob(
            job_id="job-001",
            status=GenerationJobStatus.FAILED,
            units=[
                unit(
                    "project:game_server",
                    GenerationUnitKind.PROJECT,
                    PROJECT_HASH,
                )
            ],
        )


def test_job_rejects_unknown_manifest_unit() -> None:
    with pytest.raises(ValidationError, match="정의되지 않은"):
        GenerationJob(
            job_id="job-001",
            status=GenerationJobStatus.GENERATING,
            units=[
                unit(
                    "project:game_server",
                    GenerationUnitKind.PROJECT,
                    PROJECT_HASH,
                )
            ],
            manifest=job_manifest(),
        )


def test_job_rejects_mismatched_unit_specification() -> None:
    with pytest.raises(ValidationError, match="Specification"):
        GenerationJob(
            job_id="job-001",
            status=GenerationJobStatus.GENERATING,
            units=[
                unit(
                    "project:game_server",
                    GenerationUnitKind.PROJECT,
                    content_hash("different project specification"),
                )
            ],
            manifest=GenerationJobManifest(
                job_id="job-001",
                units=[job_manifest().units[0]],
            ),
        )


def test_job_submission_normalizes_safe_relative_paths() -> None:
    submission = GenerationJobSubmission(
        project_path="spec/project.yaml",
        specifications_path="spec/modules",
        output_path="work/generated",
    )

    assert submission.project_path == "spec/project.yaml"
    with pytest.raises(ValidationError, match="드라이브"):
        GenerationJobSubmission(
            project_path="C:/outside/project.yaml",
            specifications_path="spec/modules",
            output_path="work/generated",
        )
    with pytest.raises(ValidationError, match=r"\.\."):
        GenerationJobSubmission(
            project_path="../project.yaml",
            specifications_path="spec/modules",
            output_path="work/generated",
        )
