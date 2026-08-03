import pytest

from autoforge.core.generation import content_hash
from autoforge.core.job import (
    GenerationJob,
    GenerationJobStateMachine,
    GenerationJobStatus,
    GenerationUnit,
    GenerationUnitKind,
    InvalidJobTransitionError,
)
from autoforge.core.job.models import GenerationJobManifest
from tests.core.test_generation_job import job_manifest


def _pending_job() -> GenerationJob:
    return GenerationJob(
        job_id="job-001",
        units=[
            GenerationUnit(
                unit_id="project:game_server",
                kind=GenerationUnitKind.PROJECT,
                specification_version="1",
                specification_hash=content_hash("project specification"),
            ),
            GenerationUnit(
                unit_id="module:tutorial",
                kind=GenerationUnitKind.MODULE,
                specification_version="1",
                specification_hash=content_hash("module specification"),
            ),
        ],
    )


def test_state_machine_creates_new_snapshots_for_successful_lifecycle() -> None:
    pending = _pending_job()
    generating = GenerationJobStateMachine.transition(
        pending, GenerationJobStatus.GENERATING
    )
    validating = GenerationJobStateMachine.transition(
        generating,
        GenerationJobStatus.VALIDATING,
        manifest=job_manifest(),
    )
    succeeded = GenerationJobStateMachine.transition(
        validating, GenerationJobStatus.SUCCEEDED
    )

    assert pending.status is GenerationJobStatus.PENDING
    assert generating.status is GenerationJobStatus.GENERATING
    assert validating.status is GenerationJobStatus.VALIDATING
    assert succeeded.status is GenerationJobStatus.SUCCEEDED
    assert succeeded.manifest == job_manifest()


def test_state_machine_rejects_skipping_validation() -> None:
    generating = GenerationJobStateMachine.transition(
        _pending_job(), GenerationJobStatus.GENERATING
    )

    with pytest.raises(InvalidJobTransitionError, match="cannot transition"):
        GenerationJobStateMachine.transition(
            generating,
            GenerationJobStatus.SUCCEEDED,
            manifest=job_manifest(),
        )


def test_state_machine_requires_manifest_before_validation() -> None:
    generating = GenerationJobStateMachine.transition(
        _pending_job(), GenerationJobStatus.GENERATING
    )

    with pytest.raises(InvalidJobTransitionError, match="requires a manifest"):
        GenerationJobStateMachine.transition(
            generating, GenerationJobStatus.VALIDATING
        )


def test_state_machine_supports_failure_without_mutating_previous_snapshot() -> None:
    pending = _pending_job()
    failed = GenerationJobStateMachine.transition(
        pending,
        GenerationJobStatus.FAILED,
        error="SpecificationValidationError",
    )

    assert pending.status is GenerationJobStatus.PENDING
    assert pending.error is None
    assert failed.status is GenerationJobStatus.FAILED
    assert failed.error == "SpecificationValidationError"


def test_state_machine_revalidates_manifest_before_success() -> None:
    generating = GenerationJobStateMachine.transition(
        _pending_job(), GenerationJobStatus.GENERATING
    )
    partial_manifest = GenerationJobManifest(
        job_id="job-001", units=[job_manifest().units[0]]
    )
    validating = GenerationJobStateMachine.transition(
        generating,
        GenerationJobStatus.VALIDATING,
        manifest=partial_manifest,
    )

    with pytest.raises(InvalidJobTransitionError, match="job invariants"):
        GenerationJobStateMachine.transition(
            validating, GenerationJobStatus.SUCCEEDED
        )
