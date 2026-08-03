from pydantic import ValidationError

from autoforge.core.job.models import (
    GenerationJob,
    GenerationJobManifest,
    GenerationJobStatus,
    GenerationJobSubmission,
    GenerationUnit,
)

_ALLOWED_TRANSITIONS: dict[GenerationJobStatus, frozenset[GenerationJobStatus]] = {
    GenerationJobStatus.PENDING: frozenset(
        {GenerationJobStatus.GENERATING, GenerationJobStatus.FAILED}
    ),
    GenerationJobStatus.GENERATING: frozenset(
        {GenerationJobStatus.VALIDATING, GenerationJobStatus.FAILED}
    ),
    GenerationJobStatus.VALIDATING: frozenset(
        {GenerationJobStatus.SUCCEEDED, GenerationJobStatus.FAILED}
    ),
    GenerationJobStatus.SUCCEEDED: frozenset(),
    GenerationJobStatus.FAILED: frozenset(),
}


class InvalidJobTransitionError(ValueError):
    pass


class GenerationJobStateMachine:
    """Create validated job snapshots without mutating the current snapshot."""

    @staticmethod
    def plan(
        job: GenerationJob,
        units: list[GenerationUnit],
        *,
        submission: GenerationJobSubmission | None = None,
    ) -> GenerationJob:
        if job.status is not GenerationJobStatus.PENDING:
            raise InvalidJobTransitionError("Only a pending GenerationJob may be planned")
        if job.units:
            raise InvalidJobTransitionError("GenerationJob is already planned")
        if not units:
            raise InvalidJobTransitionError("GenerationJob planning requires units")
        values = job.model_dump()
        values["units"] = units
        if submission is not None:
            values["submission"] = submission
        try:
            return GenerationJob.model_validate(values)
        except ValidationError as error_detail:
            raise InvalidJobTransitionError(
                "GenerationJob planning violates job invariants"
            ) from error_detail

    @staticmethod
    def transition(
        job: GenerationJob,
        status: GenerationJobStatus,
        *,
        manifest: GenerationJobManifest | None = None,
        error: str | None = None,
    ) -> GenerationJob:
        if status not in _ALLOWED_TRANSITIONS[job.status]:
            raise InvalidJobTransitionError(
                f"GenerationJob cannot transition from {job.status} to {status}"
            )
        next_manifest = manifest if manifest is not None else job.manifest
        if status is GenerationJobStatus.VALIDATING and next_manifest is None:
            raise InvalidJobTransitionError(
                "GenerationJob requires a manifest before validation"
            )
        if status is GenerationJobStatus.SUCCEEDED and manifest is not None:
            next_manifest = manifest
        if status is GenerationJobStatus.FAILED:
            if error is None or not error.strip():
                raise InvalidJobTransitionError(
                    "Failed GenerationJob requires a non-empty error"
                )
            next_error = error
        else:
            if error is not None:
                raise InvalidJobTransitionError(
                    "Only a failed GenerationJob may contain an error"
                )
            next_error = None
        values = job.model_dump()
        values.update(
            status=status,
            manifest=next_manifest,
            error=next_error,
        )
        try:
            return GenerationJob.model_validate(values)
        except ValidationError as error_detail:
            raise InvalidJobTransitionError(
                "GenerationJob transition violates job invariants"
            ) from error_detail
