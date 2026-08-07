from pathlib import PurePosixPath

import pytest

from autoforge.core.generation import content_hash
from autoforge.core.git import GitCheckoutRequest, GitCommitResult, GitPushResult
from autoforge.core.job import (
    GenerationJob,
    GenerationJobStateMachine,
    GenerationJobStatus,
    GenerationJobSubmission,
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


def test_unplanned_job_is_only_valid_while_pending() -> None:
    pending = GenerationJob(job_id="remote-job")

    assert pending.units == []
    with pytest.raises(InvalidJobTransitionError, match="job invariants"):
        GenerationJobStateMachine.transition(
            pending, GenerationJobStatus.GENERATING
        )


def test_state_machine_plans_pending_job_once() -> None:
    pending = GenerationJob(job_id="remote-job")
    units = _pending_job().units

    planned = GenerationJobStateMachine.plan(pending, units)

    assert pending.units == []
    assert planned.units == units
    with pytest.raises(InvalidJobTransitionError, match="already planned"):
        GenerationJobStateMachine.plan(planned, units)


def test_remote_job_commits_after_validation_and_persists_result() -> None:
    pending = GenerationJob.model_validate(
        {
            **_pending_job().model_dump(),
            "submission": GenerationJobSubmission(
                project_path="spec/project.yaml",
                specifications_path="spec/modules",
                output_path=".",
                repository=GitCheckoutRequest(
                    "https://github.com/example/repository.git", "main"
                ),
                resolved_commit_sha="a" * 40,
            ),
        }
    )
    generating = GenerationJobStateMachine.transition(
        pending, GenerationJobStatus.GENERATING
    )
    validating = GenerationJobStateMachine.transition(
        generating,
        GenerationJobStatus.VALIDATING,
        manifest=job_manifest(),
    )
    committing = GenerationJobStateMachine.transition(
        validating, GenerationJobStatus.COMMITTING
    )
    commit = GitCommitResult(
        commit_sha="b" * 40,
        branch_name="autoforge/job-001",
        changed_paths=(PurePosixPath("src/service.py"),),
        commit_created=True,
    )
    pushing = GenerationJobStateMachine.transition(
        committing,
        GenerationJobStatus.PUSHING,
        git_commit=commit,
    )
    push = GitPushResult(
        commit_sha="b" * 40,
        branch_name="autoforge/job-001",
        remote_url="https://github.com/example/repository.git",
        pushed=True,
    )
    succeeded = GenerationJobStateMachine.transition(
        pushing,
        GenerationJobStatus.SUCCEEDED,
        git_push=push,
    )

    assert committing.status is GenerationJobStatus.COMMITTING
    assert committing.git_commit is None
    assert pushing.status is GenerationJobStatus.PUSHING
    assert pushing.git_commit == commit
    assert succeeded.status is GenerationJobStatus.SUCCEEDED
    assert succeeded.git_commit == commit
    assert succeeded.git_push == push
