from autoforge.application.generation.pipeline import (
    GenerationJobRequest,
    build_generation_job,
    load_generation_specifications,
)
from autoforge.core.event import EventBus
from autoforge.core.job import (
    GenerationJob,
    GenerationJobPlannedEvent,
    GenerationJobStateMachine,
    GenerationJobSubmission,
    JobLease,
    JobStore,
)


class GenerationPlanningService:
    def __init__(self, *, job_store: JobStore, event_bus: EventBus) -> None:
        self._job_store = job_store
        self._event_bus = event_bus

    async def plan(
        self,
        lease: JobLease,
        request: GenerationJobRequest,
        *,
        submission: GenerationJobSubmission | None = None,
    ) -> GenerationJob:
        project_spec, module_specs = load_generation_specifications(
            request.project_path,
            request.specifications_path,
        )
        candidate = build_generation_job(
            lease.job.job_id,
            project_spec,
            module_specs,
            submission=lease.job.submission,
        )
        planned = GenerationJobStateMachine.plan(
            lease.job, candidate.units, submission=submission
        )
        await self._job_store.replace(
            planned,
            expected_status=lease.job.status,
            lease_token=lease.token,
        )
        await self._event_bus.publish(
            GenerationJobPlannedEvent(
                unit_ids=tuple(unit.unit_id for unit in planned.units),
                job_id=planned.job_id,
                correlation_id=planned.job_id,
                producer="generation_planning_service",
            )
        )
        return planned
