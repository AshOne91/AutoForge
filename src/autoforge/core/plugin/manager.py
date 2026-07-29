from autoforge.core.plugin.base import Plugin
from autoforge.core.registry.registry import Registry


class PluginManager:

    def __init__(self):
        self._registry = Registry[Plugin]()

    def register(self, plugin: Plugin) -> None:
        name = plugin.metadata.name

        if self._registry.exists(name):
            raise ValueError(
                f"Plugin '{name}' already registered."
            )

        self._registry.register(name, plugin)

    def get(self, name: str) -> Plugin:
        return self._registry.get(name)

    def execute(self, name: str, context):
        plugin = self.get(name)
        return plugin.execute(context)

    def list_registry(self) -> list[str]:
        return self._registry.names()
    
    def exists(self, name: str) -> bool:
        return self._registry.exists(name)

    def unregister(self, name: str) -> None:
        self._registry.unregister(name)