from collections.abc import Mapping
from pathlib import PurePosixPath

from autoforge.core.generation import GenerationPlan, Generator
from autoforge.core.plugin.metadata import (
    PluginCapability,
    PluginMetadata,
    validate_plugin_api_version,
)
from autoforge.core.registry.registry import Registry


class GeneratorPluginAdapter[SpecificationT]:
    """기존 Generator를 Plugin Metadata와 결합하는 타입 안전 Adapter."""

    def __init__(
        self,
        generator: Generator[SpecificationT],
        metadata: PluginMetadata,
    ) -> None:
        validate_plugin_api_version(metadata)
        if PluginCapability.GENERATOR not in metadata.capabilities:
            raise ValueError("Generator Plugin에는 generator Capability가 필요합니다.")
        if not metadata.supported_specification_versions:
            raise ValueError(
                "Generator Plugin에는 지원 Specification 버전이 필요합니다."
            )
        if metadata.name != generator.generator_id:
            raise ValueError("Plugin 이름과 Generator ID가 일치해야 합니다.")
        if metadata.version != generator.generator_version:
            raise ValueError("Plugin 버전과 Generator 버전이 일치해야 합니다.")
        self._generator = generator
        self._metadata = metadata

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    @property
    def generator_id(self) -> str:
        return self._generator.generator_id

    @property
    def generator_version(self) -> str:
        return self._generator.generator_version

    def render(
        self,
        specification: SpecificationT,
    ) -> Mapping[PurePosixPath, str]:
        self._validate_specification_version(specification)
        return self._generator.render(specification)

    def plan(self, specification: SpecificationT) -> GenerationPlan:
        self._validate_specification_version(specification)
        return self._generator.plan(specification)

    def _validate_specification_version(self, specification: SpecificationT) -> None:
        specification_version = getattr(specification, "spec_version", None)
        if specification_version not in self._metadata.supported_specification_versions:
            raise ValueError(
                f"지원하지 않는 Specification 버전입니다: {specification_version}"
            )


class GeneratorPluginRegistry[SpecificationT]:
    """Specification 타입별 Generator Plugin 저장소."""

    def __init__(self) -> None:
        self._registry = Registry[GeneratorPluginAdapter[SpecificationT]]()

    def register(self, plugin: GeneratorPluginAdapter[SpecificationT]) -> None:
        self._registry.register(plugin.generator_id, plugin)

    def get(self, generator_id: str) -> GeneratorPluginAdapter[SpecificationT]:
        return self._registry.get(generator_id)

    def exists(self, generator_id: str) -> bool:
        return self._registry.exists(generator_id)

    def names(self) -> list[str]:
        return self._registry.names()

    def unregister(self, generator_id: str) -> None:
        self._registry.unregister(generator_id)
