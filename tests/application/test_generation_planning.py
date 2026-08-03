import asyncio
from datetime import timedelta
from pathlib import Path

from autoforge.application.generation import (
    GenerationJobRequest,
    GenerationPlanningService,
)
from autoforge.core.event import Event, EventBus, EventHandler
from autoforge.core.job import (
    GenerationJob,
    GenerationJobPlannedEvent,
    GenerationJobSubmission,
)
from autoforge.infrastructure.job import InMemoryJobStore


class RecordingHandler(EventHandler):
    def __init__(self) -> None:
        self.events: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.events.append(event)


def _write_specifications(root: Path) -> GenerationJobRequest:
    modules = root / "spec" / "modules"
    modules.mkdir(parents=True)
    project = root / "spec" / "project.yaml"
    project.write_text(
        """spec_version: "1"
project:
  name: Sample
  package_name: sample
  version: "0.1.0"
application:
  modules:
    - account
""",
        encoding="utf-8",
    )
    (modules / "account.yaml").write_text(
        """spec_version: "1"
module:
  name: account
  display_name: Account
  route_prefix: /account
""",
        encoding="utf-8",
    )
    return GenerationJobRequest(
        project_path=project,
        specifications_path=modules,
        output_path=root,
    )


def test_planning_persists_units_with_lease_and_publishes_event(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        request = _write_specifications(tmp_path)
        store = InMemoryJobStore()
        bus = EventBus()
        handler = RecordingHandler()
        bus.subscribe(GenerationJobPlannedEvent, handler)
        job = GenerationJob(
            job_id="remote-job",
            submission=GenerationJobSubmission(
                project_path="spec/project.yaml",
                specifications_path="spec/modules",
                output_path=".",
            ),
        )
        await store.create(job)
        lease = await store.claim_next(
            worker_id="worker-1",
            lease_duration=timedelta(seconds=30),
        )
        assert lease is not None

        planned = await GenerationPlanningService(
            job_store=store, event_bus=bus
        ).plan(lease, request)

        persisted = await store.get(job.job_id)
        assert persisted == planned
        assert len(planned.units) == 2
        assert [type(event) for event in handler.events] == [
            GenerationJobPlannedEvent
        ]

    asyncio.run(scenario())
