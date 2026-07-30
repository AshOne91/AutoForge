import pytest

from autoforge.core.plugin import (
    PluginCapability,
    PluginMetadata,
    ValidatorPluginAdapter,
    ValidatorPluginRegistry,
)


async def validate_text(request: str) -> int:
    return len(request)


def metadata(**updates: object) -> PluginMetadata:
    values: dict[str, object] = {
        "name": "validator.text",
        "version": "0.1.0",
        "capabilities": (PluginCapability.VALIDATOR,),
    }
    values.update(updates)
    return PluginMetadata(**values)  # type: ignore[arg-type]


def validator_plugin(
    plugin_metadata: PluginMetadata | None = None,
) -> ValidatorPluginAdapter[str, int]:
    return ValidatorPluginAdapter(
        validator_id="validator.text",
        validator_version="0.1.0",
        validate=validate_text,
        metadata=plugin_metadata or metadata(),
    )


@pytest.mark.anyio
async def test_validator_adapter_preserves_async_types() -> None:
    plugin = validator_plugin()

    assert plugin.validator_id == "validator.text"
    assert plugin.validator_version == "0.1.0"
    assert await plugin.validate("request") == 7


@pytest.mark.parametrize(
    ("plugin_metadata", "message"),
    [
        (
            metadata(capabilities=(PluginCapability.GENERATOR,)),
            "validator Capability",
        ),
        (metadata(name="different"), "Validator ID"),
        (metadata(version="9.9.9"), "Validator 버전"),
        (metadata(api_version="999"), "Plugin API"),
    ],
)
def test_validator_adapter_rejects_inconsistent_metadata(
    plugin_metadata: PluginMetadata,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validator_plugin(plugin_metadata)


@pytest.mark.anyio
async def test_validator_registry_registers_and_retrieves_plugin() -> None:
    registry = ValidatorPluginRegistry[str, int]()
    plugin = validator_plugin()

    registry.register(plugin)

    assert registry.get(plugin.validator_id) is plugin
    assert registry.names() == ["validator.text"]
    assert await registry.get("validator.text").validate("abc") == 3


def test_validator_registry_rejects_duplicate_id() -> None:
    registry = ValidatorPluginRegistry[str, int]()
    registry.register(validator_plugin())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(validator_plugin())
