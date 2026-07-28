from autoforge.core.plugin.base import Plugin


class PluginManager:

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin):
        name = plugin.metadata.name

        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' already registered.")

        plugin.initialize()
        self._plugins[name] = plugin

    def get(self, name: str) -> Plugin:
        return self._plugins[name]

    def execute(self, name: str, context):
        plugin = self.get(name)
        return plugin.execute(context)

    def list_plugins(self):
        return sorted(self._plugins.keys())

    def exists(self, name: str) -> bool:
        return name in self._plugins

    def unregister(self, name: str):
        if not self.exists(name):
            return

        del self._plugins[name]