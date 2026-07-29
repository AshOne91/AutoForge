import pytest

from autoforge.core.config import ConfigManager, Settings
from autoforge.core.context.plugin_context import PluginContext
from autoforge.core.plugin.base import Plugin
from autoforge.core.plugin.manager import PluginManager
from autoforge.core.plugin.metadata import PluginMetadata
from autoforge.models.plugin_result import PluginResult


def config_manager() -> ConfigManager:
    settings = Settings.model_validate(
        {
            "project": {"name": "AutoForge", "version": "0.1.0"},
            "workspace": {"output": "./output"},
            "logging": {"level": "INFO"},
        }
    )
    return ConfigManager(settings)


class StubPlugin(Plugin):
    def __init__(self, name: str) -> None:
        self._metadata = PluginMetadata(name=name, version="0.1.0")
        self.executed_context: PluginContext | None = None

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def initialize(self) -> None:
        pass

    def execute(self, context: PluginContext) -> PluginResult:
        self.executed_context = context
        return PluginResult(success=True, message=f"{self.metadata.name} executed.")


def test_register_execute_and_unregister_plugin() -> None:
    manager = PluginManager()
    plugin = StubPlugin("sample")

    manager.register(plugin)

    assert manager.list_plugins() == ["sample"]
    assert manager.get("sample") is plugin
    assert manager.exists("sample")

    context = PluginContext(config=config_manager())
    result = manager.execute("sample", context)

    assert result.success
    assert result.message == "sample executed."
    assert plugin.executed_context is context

    manager.unregister("sample")

    assert not manager.exists("sample")


def test_register_duplicate_plugin_raises_value_error() -> None:
    manager = PluginManager()
    manager.register(StubPlugin("sample"))

    with pytest.raises(ValueError, match="Plugin 'sample' already registered"):
        manager.register(StubPlugin("sample"))


def test_get_missing_plugin_raises_key_error() -> None:
    manager = PluginManager()

    with pytest.raises(KeyError, match="missing"):
        manager.get("missing")


def test_list_plugins_returns_sorted_names() -> None:
    manager = PluginManager()
    manager.register(StubPlugin("second"))
    manager.register(StubPlugin("first"))

    assert manager.list_plugins() == ["first", "second"]
    assert manager.list_registry() == ["first", "second"]
