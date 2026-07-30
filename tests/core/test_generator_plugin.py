import pytest

from autoforge.core.generation import Generator
from autoforge.core.plugin import (
    GeneratorPluginAdapter,
    GeneratorPluginRegistry,
    PluginCapability,
    PluginMetadata,
)
from autoforge.core.specification import ApplicationSpec, ProjectInfo, ProjectSpec
from autoforge.services.generation import FastAPIProjectGenerator


def project_specification(spec_version: str = "1") -> ProjectSpec:
    return ProjectSpec(
        spec_version=spec_version,
        project=ProjectInfo(
            name="Game Server",
            package_name="game_server",
            version="0.1.0",
        ),
        application=ApplicationSpec(),
    )


def generator_metadata(**updates: object) -> PluginMetadata:
    values: dict[str, object] = {
        "name": "autoforge.generator.fastapi.project",
        "version": "0.1.0",
        "api_version": "1",
        "capabilities": (PluginCapability.GENERATOR,),
        "supported_specification_versions": ("1",),
    }
    values.update(updates)
    return PluginMetadata(**values)  # type: ignore[arg-type]


def test_adapter_preserves_generator_contract() -> None:
    adapter = GeneratorPluginAdapter(
        FastAPIProjectGenerator(),
        generator_metadata(),
    )

    assert isinstance(adapter, Generator)
    assert adapter.generator_id == "autoforge.generator.fastapi.project"
    assert adapter.generator_version == "0.1.0"
    assert adapter.render(project_specification())
    assert adapter.plan(project_specification()).files


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        (
            generator_metadata(capabilities=(PluginCapability.VALIDATOR,)),
            "generator Capability",
        ),
        (
            generator_metadata(supported_specification_versions=()),
            "Specification 버전",
        ),
        (
            generator_metadata(name="different.generator"),
            "Generator ID",
        ),
        (
            generator_metadata(version="9.9.9"),
            "Generator 버전",
        ),
    ],
)
def test_adapter_rejects_inconsistent_metadata(
    metadata: PluginMetadata,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        GeneratorPluginAdapter(FastAPIProjectGenerator(), metadata)


def test_adapter_rejects_unsupported_specification_version() -> None:
    adapter = GeneratorPluginAdapter(
        FastAPIProjectGenerator(),
        generator_metadata(supported_specification_versions=("2",)),
    )

    with pytest.raises(ValueError, match="지원하지 않는"):
        adapter.render(project_specification())


def test_adapter_rejects_unsupported_plugin_api_version() -> None:
    with pytest.raises(ValueError, match="Plugin API"):
        GeneratorPluginAdapter(
            FastAPIProjectGenerator(),
            generator_metadata(api_version="999"),
        )


def test_metadata_rejects_duplicate_capability() -> None:
    with pytest.raises(ValueError, match="Capability"):
        generator_metadata(
            capabilities=(
                PluginCapability.GENERATOR,
                PluginCapability.GENERATOR,
            )
        )


def test_typed_registry_registers_and_retrieves_generator_plugin() -> None:
    registry = GeneratorPluginRegistry[ProjectSpec]()
    plugin = GeneratorPluginAdapter(
        FastAPIProjectGenerator(),
        generator_metadata(),
    )

    registry.register(plugin)

    assert registry.get(plugin.generator_id) is plugin
    assert registry.exists(plugin.generator_id)
    assert registry.names() == [plugin.generator_id]


def test_typed_registry_rejects_duplicate_generator_id() -> None:
    registry = GeneratorPluginRegistry[ProjectSpec]()
    registry.register(
        GeneratorPluginAdapter(
            FastAPIProjectGenerator(),
            generator_metadata(),
        )
    )

    with pytest.raises(ValueError, match="already registered"):
        registry.register(
            GeneratorPluginAdapter(
                FastAPIProjectGenerator(),
                generator_metadata(),
            )
        )
