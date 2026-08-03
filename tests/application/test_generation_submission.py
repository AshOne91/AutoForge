import asyncio
from pathlib import Path

import pytest

from autoforge.application.generation import (
    GenerationSubmissionService,
    GenerationTriggerRequest,
    IdempotencyConflictError,
)
from autoforge.core.event import Event, EventBus, EventHandler
from autoforge.core.job import GenerationJobCreatedEvent
from autoforge.infrastructure.job import InMemoryJobStore


class RecordingHandler(EventHandler):
    def __init__(self) -> None:
        self.events: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.events.append(event)


def _write_specifications(root: Path, *, module_name: str = "account") -> None:
    specification_root = root / "spec"
    modules = specification_root / "modules"
    modules.mkdir(parents=True)
    (specification_root / "project.yaml").write_text(
        "\n".join(
            (
                'spec_version: "1"',
                "project:",
                "  name: Sample",
                "  package_name: sample",
                '  version: "0.1.0"',
                "application:",
                "  modules:",
                f"    - {module_name}",
            )
        ),
        encoding="utf-8",
    )
    (modules / f"{module_name}.yaml").write_text(
        "\n".join(
            (
                'spec_version: "1"',
                "module:",
                f"  name: {module_name}",
                f"  display_name: {module_name.title()}",
                f"  route_prefix: /{module_name}",
            )
        ),
        encoding="utf-8",
    )


def _request() -> GenerationTriggerRequest:
    return GenerationTriggerRequest(
        project_path="spec/project.yaml",
        specifications_path="spec/modules",
        output_path="generated/service",
    )


def test_submission_claims_once_and_publishes_created_event(tmp_path: Path) -> None:
    async def scenario() -> None:
        _write_specifications(tmp_path)
        output_root = tmp_path / "output"
        output_root.mkdir()
        store = InMemoryJobStore()
        bus = EventBus()
        handler = RecordingHandler()
        bus.subscribe(GenerationJobCreatedEvent, handler)
        service = GenerationSubmissionService(
            source_root=tmp_path,
            output_root=output_root,
            job_store=store,
            event_bus=bus,
        )

        first = await service.trigger(_request(), idempotency_key="delivery-1")
        second = await service.trigger(_request(), idempotency_key="delivery-1")

        assert first.created is True
        assert second.created is False
        assert second.job.job_id == first.job.job_id
        assert second.job.submission == first.job.submission
        assert len(handler.events) == 1

    asyncio.run(scenario())


def test_submission_rejects_changed_request_for_same_key(tmp_path: Path) -> None:
    async def scenario() -> None:
        _write_specifications(tmp_path)
        output_root = tmp_path / "output"
        output_root.mkdir()
        service = GenerationSubmissionService(
            source_root=tmp_path,
            output_root=output_root,
            job_store=InMemoryJobStore(),
            event_bus=EventBus(),
        )
        await service.trigger(_request(), idempotency_key="delivery-1")

        changed = GenerationTriggerRequest(
            project_path="spec/project.yaml",
            specifications_path="spec/modules",
            output_path="generated/other",
        )
        with pytest.raises(IdempotencyConflictError):
            await service.trigger(changed, idempotency_key="delivery-1")

    asyncio.run(scenario())


def test_submission_rejects_paths_outside_roots(tmp_path: Path) -> None:
    _write_specifications(tmp_path)
    output_root = tmp_path / "output"
    output_root.mkdir()
    service = GenerationSubmissionService(
        source_root=tmp_path,
        output_root=output_root,
        job_store=InMemoryJobStore(),
        event_bus=EventBus(),
    )

    with pytest.raises(ValueError, match=r"\.\."):
        asyncio.run(
            service.trigger(
                GenerationTriggerRequest(
                    project_path="../project.yaml",
                    specifications_path="spec/modules",
                    output_path="generated/service",
                ),
                idempotency_key="delivery-1",
            )
        )


def test_remote_submission_creates_unplanned_job_without_local_files(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        output_root = tmp_path / "output"
        output_root.mkdir()
        service = GenerationSubmissionService(
            source_root=tmp_path,
            output_root=output_root,
            job_store=InMemoryJobStore(),
            event_bus=EventBus(),
        )

        result = await service.trigger(
            GenerationTriggerRequest(
                project_path="spec/project.yaml",
                specifications_path="spec/modules",
                output_path=".",
                repository_url="https://github.com/example/service.git",
                revision="main",
            ),
            idempotency_key="remote-delivery-1",
        )

        assert result.job.units == []
        assert result.job.submission is not None
        assert result.job.submission.repository is not None
        assert result.job.submission.repository.revision == "main"

    asyncio.run(scenario())


def test_remote_submission_requires_repository_and_revision_pair(
    tmp_path: Path,
) -> None:
    service = GenerationSubmissionService(
        source_root=tmp_path,
        output_root=tmp_path,
        job_store=InMemoryJobStore(),
        event_bus=EventBus(),
    )

    with pytest.raises(ValueError, match="provided together"):
        asyncio.run(
            service.trigger(
                GenerationTriggerRequest(
                    project_path="spec/project.yaml",
                    specifications_path="spec/modules",
                    output_path=".",
                    repository_url="https://github.com/example/service.git",
                ),
                idempotency_key="remote-delivery-1",
            )
        )
