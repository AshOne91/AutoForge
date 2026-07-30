from autoforge.core.context.plugin_context import PluginContext
from autoforge.core.plugin.base import Plugin
from autoforge.core.plugin.metadata import validate_plugin_api_version
from autoforge.core.registry.registry import Registry
from autoforge.models.plugin_result import PluginResult


class PluginManager:
    def __init__(self) -> None:
        self._registry = Registry[Plugin]()

    def register(self, plugin: Plugin) -> None:
        validate_plugin_api_version(plugin.metadata)
        name = plugin.metadata.name

        if self._registry.exists(name):
            raise ValueError(f"Plugin '{name}' already registered.")

        self._registry.register(name, plugin)

    def get(self, name: str) -> Plugin:
        return self._registry.get(name)

    def execute(
        self,
        name: str,
        context: PluginContext,
    ) -> PluginResult:
        plugin = self._registry.get(name)
        return plugin.execute(context)

    def list_plugins(self) -> list[str]:
        return self._registry.names()

    def list_registry(self) -> list[str]:
        return self.list_plugins()

    def exists(self, name: str) -> bool:
        return self._registry.exists(name)

    def unregister(self, name: str) -> None:
        self._registry.unregister(name)
