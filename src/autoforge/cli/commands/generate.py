from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
import yaml

from autoforge.core.job import (
    GenerationJobManifest,
    GenerationUnitKind,
    GenerationUnitManifest,
)
from autoforge.core.specification import EndpointDependency, ModuleSpec, ProjectSpec
from autoforge.core.workspace import Workspace
from autoforge.services.generation import GenerationRunner, ManifestStore
from autoforge.services.generation.manifest_store import ManifestStoreError
from autoforge.services.generation.plugin_registry import (
    create_fastapi_generator_plugins,
)

app = typer.Typer()


@app.callback(invoke_without_command=True)
def generate(
    project: Annotated[Path, typer.Option(exists=True)] = Path("autoforge.yaml"),
    specifications: Annotated[Path, typer.Option(exists=True)] = Path(
        "specifications"
    ),
    output: Annotated[Path, typer.Option()] = Path("."),
) -> None:
    """명세를 검증하고 등록된 Generator 결과를 대상 Workspace에 적용한다."""
    project_spec = ProjectSpec.model_validate(_load_yaml(project))
    module_specs = [ModuleSpec.model_validate(_load_yaml(path)) for path in sorted(specifications.glob("*.yaml"))]
    declared = set(project_spec.application.modules)
    discovered = {spec.module.name for spec in module_specs}
    if declared != discovered:
        raise typer.BadParameter(
            "Module 명세가 Project 선언과 일치하지 않습니다: "
            f"declared={sorted(declared)}, discovered={sorted(discovered)}"
        )
    _validate_endpoint_dependencies(project_spec, module_specs)
    _validate_database_placements(project_spec, module_specs)

    output.mkdir(parents=True, exist_ok=True)
    workspace = Workspace(output.resolve())
    store = ManifestStore(workspace)
    previous = _load_previous_job(store)
    previous_units = (
        {(unit.unit_id, unit.kind): unit.manifest for unit in previous.units}
        if previous is not None
        else {}
    )
    plugins = create_fastapi_generator_plugins(project_spec.project.package_name)
    job_id = str(uuid4())
    units: list[GenerationUnitManifest] = []

    project_manifest = GenerationRunner[ProjectSpec]().run(
        job_id=job_id,
        specification=project_spec,
        generators=[plugins.project.get(name) for name in plugins.project.names()],
        workspace=workspace,
        manifest=previous_units.get(("project", GenerationUnitKind.PROJECT)),
    )
    units.append(GenerationUnitManifest(unit_id="project", kind=GenerationUnitKind.PROJECT, manifest=project_manifest))

    for module_spec in module_specs:
        unit_id = f"module:{module_spec.module.name}"
        manifest = GenerationRunner[ModuleSpec]().run(
            job_id=job_id,
            specification=module_spec,
            generators=[plugins.module.get(name) for name in plugins.module.names()],
            workspace=workspace,
            manifest=previous_units.get((unit_id, GenerationUnitKind.MODULE)),
        )
        units.append(GenerationUnitManifest(unit_id=unit_id, kind=GenerationUnitKind.MODULE, manifest=manifest))

    store.save_job(GenerationJobManifest(job_id=job_id, units=units))
    typer.echo(f"Generated {len(units)} units in {workspace.root}")


def _load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _validate_endpoint_dependencies(
    project_spec: ProjectSpec,
    module_specs: list[ModuleSpec],
) -> None:
    requires_session_store = any(
        EndpointDependency.SESSION_STORE in endpoint.dependencies
        for module_spec in module_specs
        for endpoint in module_spec.endpoints
    )
    has_session_store = any(
        service.kind == "redis_session"
        for service in project_spec.application.services
    )
    if requires_session_store and not has_session_store:
        raise typer.BadParameter(
            "Endpoint dependency 'session_store' requires a redis_session service."
        )


def _validate_database_placements(
    project_spec: ProjectSpec,
    module_specs: list[ModuleSpec],
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
        raise typer.BadParameter(
            "Database placement references undeclared stores: "
            + ", ".join(unknown)
        )


def _load_previous_job(store: ManifestStore) -> GenerationJobManifest | None:
    if not store.path.is_file():
        return None
    try:
        return store.load_job()
    except ManifestStoreError as error:
        raise typer.BadParameter(str(error)) from error
