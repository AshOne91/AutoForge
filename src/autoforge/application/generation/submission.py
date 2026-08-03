from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from autoforge.application.generation.pipeline import (
    build_generation_job,
    load_generation_specifications,
)
from autoforge.core.event import EventBus
from autoforge.core.git import GitCheckoutRequest
from autoforge.core.job import (
    GenerationJob,
    GenerationJobCreatedEvent,
    GenerationJobSubmission,
    JobStore,
)
from autoforge.core.workspace import Workspace


class IdempotencyConflictError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GenerationTriggerRequest:
    project_path: str
    specifications_path: str
    output_path: str
    repository_url: str | None = None
    revision: str | None = None

    def submission(self) -> GenerationJobSubmission:
        if (self.repository_url is None) != (self.revision is None):
            raise ValueError(
                "repository_url and revision must be provided together"
            )
        repository = (
            GitCheckoutRequest(self.repository_url, self.revision)
            if self.repository_url is not None and self.revision is not None
            else None
        )
        return GenerationJobSubmission(
            project_path=self.project_path,
            specifications_path=self.specifications_path,
            output_path=self.output_path,
            repository=repository,
        )


@dataclass(frozen=True, slots=True)
class GenerationTriggerResult:
    job: GenerationJob
    created: bool


class GenerationSubmissionService:
    def __init__(
        self,
        *,
        source_root: Path,
        output_root: Path,
        job_store: JobStore,
        event_bus: EventBus,
    ) -> None:
        self._source = Workspace(source_root)
        self._output = Workspace(output_root)
        self._job_store = job_store
        self._event_bus = event_bus

    async def trigger(
        self,
        request: GenerationTriggerRequest,
        *,
        idempotency_key: str,
    ) -> GenerationTriggerResult:
        key = idempotency_key.strip()
        if not key or len(key) > 255:
            raise ValueError("idempotency_key must contain 1 to 255 characters")

        submission = request.submission()
        if submission.repository is None:
            project_path = self._source.resolve(submission.project_path)
            specifications_path = self._source.resolve(
                submission.specifications_path
            )
            self._output.resolve(submission.output_path)
            if not project_path.is_file():
                raise ValueError("project_path must reference an existing file")
            if not specifications_path.is_dir():
                raise ValueError(
                    "specifications_path must reference an existing directory"
                )
            project_spec, module_specs = load_generation_specifications(
                project_path, specifications_path
            )
            job = build_generation_job(
                str(uuid4()),
                project_spec,
                module_specs,
                submission=submission,
            )
        else:
            job = GenerationJob(
                job_id=str(uuid4()),
                submission=submission,
            )
        claim = await self._job_store.create_or_get(
            job, idempotency_key=key
        )
        if not claim.created and (
            _requested_submission(claim.job.submission) != job.submission
            or (bool(job.units) and claim.job.units != job.units)
        ):
            raise IdempotencyConflictError(
                "idempotency_key is already associated with another request"
            )
        if claim.created:
            await self._event_bus.publish(
                GenerationJobCreatedEvent(
                    unit_ids=tuple(unit.unit_id for unit in job.units),
                    job_id=job.job_id,
                    correlation_id=job.job_id,
                    producer="generation_submission_service",
                )
            )
        return GenerationTriggerResult(claim.job, claim.created)

    async def get(self, job_id: str) -> GenerationJob | None:
        return await self._job_store.get(job_id)


def _requested_submission(
    submission: GenerationJobSubmission | None,
) -> GenerationJobSubmission | None:
    if submission is None or submission.resolved_commit_sha is None:
        return submission
    return submission.model_copy(update={"resolved_commit_sha": None})
