from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

import yaml
from pydantic import ValidationError

from autoforge.core.event import EventBus
from autoforge.core.generation import specification_hash
from autoforge.core.job import (
    GenerationCompletedEvent,
    GenerationFailedEvent,
    GenerationJob,
    GenerationJobCreatedEvent,
    GenerationJobManifest,
    GenerationJobStateMachine,
    GenerationJobStatus,
    GenerationJobSubmission,
    GenerationStartedEvent,
    GenerationUnit,
    GenerationUnitKind,
    GenerationUnitManifest,
    JobStore,
    ValidationCompletedEvent,
    ValidationFailedEvent,
    ValidationStartedEvent,
)
from autoforge.core.pipeline import (
    PipelineResult,
    PipelineStep,
    SequentialPipeline,
)
from autoforge.core.specification import (
    EndpointDependency,
    ModuleSpec,
    ProjectSpec,
)
from autoforge.core.task.task import Task
from autoforge.core.workspace import Workspace
from autoforge.services.generation import GenerationRunner, ManifestStore
from autoforge.services.generation.manifest_store import ManifestStoreError
from autoforge.services.generation.plugin_registry import (
    create_fastapi_generator_plugins,
)
from autoforge.services.validation import ProjectValidationResult, ValidationStep


class GenerationSpecificationError(ValueError):
    pass


class GenerationValidationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class GenerationJobRequest:
    project_path: Path
    specifications_path: Path
    output_path: Path


@dataclass(frozen=True, slots=True)
class GenerationJobExecution:
    job: GenerationJob
    pipeline_result: PipelineResult


class ProjectValidatorProtocol(Protocol):
    async def validate(
        self, *, package_name: str, workspace: Workspace
    ) -> ProjectValidationResult: ...


@dataclass(slots=True)
class _GenerationContext:
    job_id: str
    request: GenerationJobRequest
    project_spec: ProjectSpec | None = None
    module_specs: tuple[ModuleSpec, ...] = ()
    workspace: Workspace | None = None
    job: GenerationJob | None = None
    manifest: GenerationJobManifest | None = None
    manifest_path: Path | None = None


class _PrepareGenerationJobTask(Task):
    def __init__(
        self,
        context: _GenerationContext,
        job_store: JobStore,
        event_bus: EventBus,
    ) -> None:
        self._context = context
        self._job_store = job_store
        self._event_bus = event_bus

    async def execute(self) -> GenerationJob:
        project_spec, module_specs = load_generation_specifications(
            self._context.request.project_path,
            self._context.request.specifications_path,
        )
        self._context.request.output_path.mkdir(parents=True, exist_ok=True)
        job = build_generation_job(
            self._context.job_id, project_spec, module_specs
        )
        await self._job_store.create(job)
        self._context.project_spec = project_spec
        self._context.module_specs = module_specs
        self._context.workspace = Workspace(
            self._context.request.output_path.resolve()
        )
        self._context.job = job
        await self._event_bus.publish(
            GenerationJobCreatedEvent(
                unit_ids=tuple(unit.unit_id for unit in job.units),
                **self._metadata(),
            )
        )
        return job

    def _metadata(self) -> dict[str, str]:
        return {
            "job_id": self._context.job_id,
            "correlation_id": self._context.job_id,
            "producer": "generation_application",
        }


class _GenerateUnitsTask(Task):
    def __init__(
        self,
        context: _GenerationContext,
        job_store: JobStore,
        event_bus: EventBus,
    ) -> None:
        self._context = context
        self._job_store = job_store
        self._event_bus = event_bus

    async def execute(self) -> GenerationJobManifest:
        job = self._require_job()
        generating = GenerationJobStateMachine.transition(
            job, GenerationJobStatus.GENERATING
        )
        await self._replace(generating, expected_status=job.status)
        await self._event_bus.publish(
            GenerationStartedEvent(
                unit_count=len(generating.units), **self._metadata()
            )
        )
        try:
            manifest, manifest_path = self._generate()
        except Exception as error:
            await self._fail(error)
            raise
        validating = GenerationJobStateMachine.transition(
            self._require_job(),
            GenerationJobStatus.VALIDATING,
            manifest=manifest,
        )
        await self._replace(
            validating, expected_status=GenerationJobStatus.GENERATING
        )
        self._context.manifest = manifest
        self._context.manifest_path = manifest_path
        await self._event_bus.publish(
            GenerationCompletedEvent(
                unit_count=len(manifest.units),
                manifest_path=manifest_path.relative_to(
                    self._require_workspace().root
                ).as_posix(),
                **self._metadata(),
            )
        )
        return manifest

    def _generate(self) -> tuple[GenerationJobManifest, Path]:
        project_spec = self._require_project_spec()
        workspace = self._require_workspace()
        store = ManifestStore(workspace)
        previous = _load_previous_job(store)
        previous_units = (
            {(unit.unit_id, unit.kind): unit.manifest for unit in previous.units}
            if previous is not None
            else {}
        )
        plugins = create_fastapi_generator_plugins(
            project_spec.project.package_name
        )
        units: list[GenerationUnitManifest] = []
        project_manifest = GenerationRunner[ProjectSpec]().run(
            job_id=self._context.job_id,
            specification=project_spec,
            generators=[
                plugins.project.get(name) for name in plugins.project.names()
            ],
            workspace=workspace,
            manifest=previous_units.get(
                ("project", GenerationUnitKind.PROJECT)
            ),
        )
        units.append(
            GenerationUnitManifest(
                unit_id="project",
                kind=GenerationUnitKind.PROJECT,
                manifest=project_manifest,
            )
        )
        for module_spec in self._context.module_specs:
            unit_id = f"module:{module_spec.module.name}"
            module_manifest = GenerationRunner[ModuleSpec]().run(
                job_id=self._context.job_id,
                specification=module_spec,
                generators=[
                    plugins.module.get(name) for name in plugins.module.names()
                ],
                workspace=workspace,
                manifest=previous_units.get(
                    (unit_id, GenerationUnitKind.MODULE)
                ),
            )
            units.append(
                GenerationUnitManifest(
                    unit_id=unit_id,
                    kind=GenerationUnitKind.MODULE,
                    manifest=module_manifest,
                )
            )
        manifest = GenerationJobManifest(
            job_id=self._context.job_id, units=units
        )
        return manifest, store.save_job(manifest)

    async def _fail(self, error: Exception) -> None:
        current = self._require_job()
        failed = GenerationJobStateMachine.transition(
            current,
            GenerationJobStatus.FAILED,
            error=type(error).__name__,
        )
        await self._replace(failed, expected_status=current.status)
        await self._event_bus.publish(
            GenerationFailedEvent(error_type=type(error).__name__, **self._metadata())
        )

    async def _replace(
        self, job: GenerationJob, *, expected_status: GenerationJobStatus
    ) -> None:
        await self._job_store.replace(job, expected_status=expected_status)
        self._context.job = job

    def _require_job(self) -> GenerationJob:
        if self._context.job is None:
            raise RuntimeError("GenerationJob has not been prepared")
        return self._context.job

    def _require_project_spec(self) -> ProjectSpec:
        if self._context.project_spec is None:
            raise RuntimeError("Project specification has not been loaded")
        return self._context.project_spec

    def _require_workspace(self) -> Workspace:
        if self._context.workspace is None:
            raise RuntimeError("Workspace has not been prepared")
        return self._context.workspace

    def _metadata(self) -> dict[str, str]:
        return {
            "job_id": self._context.job_id,
            "correlation_id": self._context.job_id,
            "producer": "generation_application",
        }


class _ValidateGeneratedProjectTask(Task):
    def __init__(
        self,
        context: _GenerationContext,
        job_store: JobStore,
        event_bus: EventBus,
        validator: ProjectValidatorProtocol,
    ) -> None:
        self._context = context
        self._job_store = job_store
        self._event_bus = event_bus
        self._validator = validator

    async def execute(self) -> ProjectValidationResult:
        await self._event_bus.publish(
            ValidationStartedEvent(step_count=len(ValidationStep), **self._metadata())
        )
        try:
            result = await self._validator.validate(
                package_name=self._require_project_spec().project.package_name,
                workspace=self._require_workspace(),
            )
        except Exception as error:
            await self._fail(error, failed_step="validator")
            raise
        if not result.succeeded:
            failed_step = next(
                step.step.value for step in result.steps if not step.succeeded
            )
            error = GenerationValidationError(
                f"Generated project validation failed at {failed_step}"
            )
            await self._fail(error, failed_step=failed_step)
            raise error
        current = self._require_job()
        succeeded = GenerationJobStateMachine.transition(
            current, GenerationJobStatus.SUCCEEDED
        )
        await self._job_store.replace(
            succeeded, expected_status=GenerationJobStatus.VALIDATING
        )
        self._context.job = succeeded
        completed_steps = tuple(step.step.value for step in result.steps)
        await self._event_bus.publish(
            ValidationCompletedEvent(
                completed_steps=completed_steps, **self._metadata()
            )
        )
        return result

    async def _fail(self, error: Exception, *, failed_step: str) -> None:
        current = self._require_job()
        failed = GenerationJobStateMachine.transition(
            current,
            GenerationJobStatus.FAILED,
            error=type(error).__name__,
        )
        await self._job_store.replace(
            failed, expected_status=GenerationJobStatus.VALIDATING
        )
        self._context.job = failed
        await self._event_bus.publish(
            ValidationFailedEvent(
                failed_step=failed_step,
                error_type=type(error).__name__,
                **self._metadata(),
            )
        )

    def _require_job(self) -> GenerationJob:
        if self._context.job is None:
            raise RuntimeError("GenerationJob has not been prepared")
        return self._context.job

    def _require_project_spec(self) -> ProjectSpec:
        if self._context.project_spec is None:
            raise RuntimeError("Project specification has not been loaded")
        return self._context.project_spec

    def _require_workspace(self) -> Workspace:
        if self._context.workspace is None:
            raise RuntimeError("Workspace has not been prepared")
        return self._context.workspace

    def _metadata(self) -> dict[str, str]:
        return {
            "job_id": self._context.job_id,
            "correlation_id": self._context.job_id,
            "producer": "generation_application",
        }


class GenerationJobPipeline:
    def __init__(
        self,
        *,
        job_store: JobStore,
        event_bus: EventBus,
        validator: ProjectValidatorProtocol,
    ) -> None:
        self._job_store = job_store
        self._event_bus = event_bus
        self._validator = validator

    async def run(
        self,
        request: GenerationJobRequest,
        *,
        job_id: str | None = None,
    ) -> GenerationJobExecution:
        context = _GenerationContext(
            job_id=job_id or str(uuid4()), request=request
        )
        pipeline = SequentialPipeline(
            name="generation",
            job_id=context.job_id,
            steps=(
                PipelineStep(
                    "prepare_generation_job",
                    _PrepareGenerationJobTask(
                        context, self._job_store, self._event_bus
                    ),
                ),
                PipelineStep(
                    "generate_units",
                    _GenerateUnitsTask(
                        context, self._job_store, self._event_bus
                    ),
                ),
                PipelineStep(
                    "validate_generated_project",
                    _ValidateGeneratedProjectTask(
                        context,
                        self._job_store,
                        self._event_bus,
                        self._validator,
                    ),
                ),
            ),
            event_bus=self._event_bus,
        )
        result = await pipeline.run()
        if context.job is None:
            raise RuntimeError("Generation pipeline completed without a job")
        return GenerationJobExecution(job=context.job, pipeline_result=result)


def build_generation_job(
    job_id: str,
    project_spec: ProjectSpec,
    module_specs: tuple[ModuleSpec, ...],
    *,
    submission: GenerationJobSubmission | None = None,
) -> GenerationJob:
    units = [
        GenerationUnit(
            unit_id="project",
            kind=GenerationUnitKind.PROJECT,
            specification_version=project_spec.spec_version,
            specification_hash=specification_hash(project_spec),
        ),
        *(
            GenerationUnit(
                unit_id=f"module:{module.module.name}",
                kind=GenerationUnitKind.MODULE,
                specification_version=module.spec_version,
                specification_hash=specification_hash(module),
            )
            for module in module_specs
        ),
    ]
    return GenerationJob(job_id=job_id, units=units, submission=submission)


def load_generation_specifications(
    project_path: Path, specifications_path: Path
) -> tuple[ProjectSpec, tuple[ModuleSpec, ...]]:
    try:
        project_spec = ProjectSpec.model_validate(_load_yaml(project_path))
        module_specs = tuple(
            ModuleSpec.model_validate(_load_yaml(path))
            for path in sorted(specifications_path.glob("*.yaml"))
        )
    except (OSError, ValidationError, yaml.YAMLError) as error:
        raise GenerationSpecificationError(str(error)) from error
    validate_module_declarations(project_spec, module_specs)
    validate_endpoint_dependencies(project_spec, module_specs)
    validate_database_placements(project_spec, module_specs)
    return project_spec, module_specs


def validate_module_declarations(
    project_spec: ProjectSpec, module_specs: tuple[ModuleSpec, ...]
) -> None:
    declared = set(project_spec.application.modules)
    discovered = {spec.module.name for spec in module_specs}
    if declared != discovered:
        raise GenerationSpecificationError(
            "Module specifications do not match the project declaration: "
            f"declared={sorted(declared)}, discovered={sorted(discovered)}"
        )


def validate_endpoint_dependencies(
    project_spec: ProjectSpec, module_specs: tuple[ModuleSpec, ...]
) -> None:
    requires_session_store = any(
        EndpointDependency.SESSION_STORE in endpoint.dependencies
        or EndpointDependency.CURRENT_SESSION in endpoint.dependencies
        for module_spec in module_specs
        for endpoint in module_spec.endpoints
    )
    has_session_store = any(
        service.kind == "redis_session"
        for service in project_spec.application.services
    )
    if requires_session_store and not has_session_store:
        raise GenerationSpecificationError(
            "Endpoint dependency 'session_store' requires a redis_session service."
        )


def validate_database_placements(
    project_spec: ProjectSpec, module_specs: tuple[ModuleSpec, ...]
) -> None:
    declared_stores = {
        database.name for database in project_spec.application.databases
    }
    unknown = sorted(
        {
            placement.store
            for module_spec in module_specs
            if module_spec.database is not None
            for placement in module_spec.database.placements
            if placement.store not in declared_stores
        }
    )
    if unknown:
        raise GenerationSpecificationError(
            "Database placement references undeclared stores: "
            + ", ".join(unknown)
        )


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_previous_job(store: ManifestStore) -> GenerationJobManifest | None:
    if not store.path.is_file():
        return None
    try:
        return store.load_job()
    except ManifestStoreError as error:
        raise GenerationSpecificationError(str(error)) from error
