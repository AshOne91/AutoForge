from collections.abc import Sequence
from pathlib import PurePosixPath

from autoforge.core.generation import (
    GenerationManifest,
    GenerationPlan,
    Generator,
    specification_hash,
)
from autoforge.core.specification import ModuleSpec, ProjectSpec
from autoforge.core.workspace import Workspace
from autoforge.services.generation.plan_applier import GenerationPlanApplier
from autoforge.services.generation.plan_resolver import GenerationPlanResolver


class GenerationRunnerError(RuntimeError):
    pass


class GenerationRunner[SpecificationT: (ProjectSpec, ModuleSpec)]:
    """Compose generators for one specification and apply one checked plan."""

    def __init__(
        self,
        resolver: GenerationPlanResolver | None = None,
        applier: GenerationPlanApplier | None = None,
    ) -> None:
        self._resolver = resolver or GenerationPlanResolver()
        self._applier = applier or GenerationPlanApplier()

    def run(
        self,
        *,
        job_id: str,
        specification: SpecificationT,
        generators: Sequence[Generator[SpecificationT]],
        workspace: Workspace,
        manifest: GenerationManifest | None = None,
    ) -> GenerationManifest:
        plan, rendered = self.compose(specification, generators)
        resolved = self._resolver.resolve(plan, workspace, manifest)
        return self._applier.apply(
            job_id=job_id,
            plan=resolved,
            rendered_files=rendered,
            workspace=workspace,
        )

    @staticmethod
    def compose(
        specification: SpecificationT,
        generators: Sequence[Generator[SpecificationT]],
    ) -> tuple[GenerationPlan, dict[PurePosixPath, str]]:
        if not generators:
            raise GenerationRunnerError("At least one generator is required")

        files = []
        rendered: dict[PurePosixPath, str] = {}
        owners: dict[PurePosixPath, str] = {}
        for generator in generators:
            generator_plan = generator.plan(specification)
            generator_rendered = dict(generator.render(specification))
            for planned_file in generator_plan.files:
                path = planned_file.relative_path
                previous_owner = owners.get(path)
                if previous_owner is not None:
                    raise GenerationRunnerError(
                        f"Generators produce the same path '{path}': "
                        f"{previous_owner}, {generator.generator_id}"
                    )
                owners[path] = generator.generator_id
                files.append(planned_file)
            for path, content in generator_rendered.items():
                if path in rendered:
                    raise GenerationRunnerError(
                        f"Generators rendered the same path '{path}'"
                    )
                rendered[path] = content

        return (
            GenerationPlan(
                specification_version=specification.spec_version,
                specification_hash=specification_hash(specification),
                files=sorted(files, key=lambda file: file.relative_path.as_posix()),
            ),
            rendered,
        )
