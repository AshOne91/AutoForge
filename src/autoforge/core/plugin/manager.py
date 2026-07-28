from autoforge.core.execution.context import PluginContext
from autoforge.core.plugin.base import Plugin


class PluginManager:
    """Plugin 등록 및 실행을 담당"""

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin):
        """Plugin 등록"""

        name = plugin.metadata.name

        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' already registered.")

        self._plugins[name] = plugin

    def get(self, name: str) -> Plugin:
        """Plugin 조회"""

        return self._plugins[name]

    def execute(self, name: str, context: PluginContext):
        """Plugin 실행"""

        plugin = self.get(name)

        plugin.initialize()
        plugin.execute(context)

    def list_plugins(self) -> list[str]:
        """등록된 Plugin 이름 목록"""

        return sorted(self._plugins.keys())