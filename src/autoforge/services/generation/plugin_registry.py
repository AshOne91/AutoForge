from dataclasses import dataclass

from autoforge.core.plugin import (
    GeneratorPluginAdapter,
    GeneratorPluginRegistry,
    PluginCapability,
    PluginMetadata,
)
from autoforge.core.specification import ModuleSpec, ProjectSpec
from autoforge.services.generation.fastapi_module import (
    MODULE_GENERATOR_ID,
    MODULE_GENERATOR_VERSION,
    FastAPIModuleGenerator,
)
from autoforge.services.generation.fastapi_project import (
    GENERATOR_ID,
    GENERATOR_VERSION,
    FastAPIProjectGenerator,
)


@dataclass(frozen=True, slots=True)
class FastAPIGeneratorPlugins:
    project: GeneratorPluginRegistry[ProjectSpec]
    module: GeneratorPluginRegistry[ModuleSpec]


def create_fastapi_generator_plugins(
    package_name: str,
) -> FastAPIGeneratorPlugins:
    project_registry = GeneratorPluginRegistry[ProjectSpec]()
    project_registry.register(
        GeneratorPluginAdapter(
            FastAPIProjectGenerator(),
            PluginMetadata(
                name=GENERATOR_ID,
                version=GENERATOR_VERSION,
                description="FastAPI 프로젝트 구조 Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )

    module_registry = GeneratorPluginRegistry[ModuleSpec]()
    module_registry.register(
        GeneratorPluginAdapter(
            FastAPIModuleGenerator(package_name),
            PluginMetadata(
                name=MODULE_GENERATOR_ID,
                version=MODULE_GENERATOR_VERSION,
                description="FastAPI 도메인 Module Generator",
                capabilities=(PluginCapability.GENERATOR,),
                supported_specification_versions=("1",),
            ),
        )
    )
    return FastAPIGeneratorPlugins(
        project=project_registry,
        module=module_registry,
    )
